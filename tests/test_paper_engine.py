from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from importlib import import_module
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

import pytest

from quant.core.config import load_strategy_config
from quant.core.contract import Account, OrderSide, OrderType, StrategyBase
from quant.data.service import DataService
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine
from quant.live.types import AlertSeverity, EngineState


def test_load_bars_returns_sorted_timezone_aware_bars() -> None:
    service = DataService(Path("data_sample"))

    bars = service.load_bars(["510300.SH"])

    assert [bar.dt.isoformat() for bar in bars[:3]] == [
        "2024-01-02T15:00:00+08:00",
        "2024-01-03T15:00:00+08:00",
        "2024-01-04T15:00:00+08:00",
    ]
    assert all(bar.dt.tzinfo is not None for bar in bars)
    assert all(bar.symbol == "510300.SH" for bar in bars)
    assert all(bar.freq == "1d" for bar in bars)


def test_load_bars_rejects_missing_rows() -> None:
    service = DataService(Path("data_sample"))

    with pytest.raises(ValueError, match="history contains missing data"):
        service.load_bars(["510300.SH", "159999.SZ"])


def test_paper_engine_replay_bootstraps_and_executes_targets_next_bar(
    tmp_path, monkeypatch
) -> None:
    strategy_module = ModuleType("tests.paper_strategy")

    class PaperTestStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])
            self.signal_seen = False

        def on_bar(self, ctx, bar) -> None:
            if not self.signal_seen and bar.symbol == self.symbol:
                self.signal_seen = True
                ctx.set_target(self.symbol, self.target_qty)

    strategy_module.PaperTestStrategy = PaperTestStrategy

    def fake_import_module(name: str):
        if name == "tests.paper_strategy":
            return strategy_module
        return import_module(name)

    monkeypatch.setattr("quant.live.engine.import_module", fake_import_module)

    strategy_config = load_strategy_config(
        Path("config/strategies/dual_ma_510300_paper.yaml")
    ).model_copy(
        update={
            "class_path": "tests.paper_strategy:PaperTestStrategy",
            "params": {
                "symbol": "510300.SH",
                "target_qty": 1000,
            },
            "id": "paper_test_strategy",
        }
    )
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )

    result = PaperEngine(strategy_config, paper_config).run_replay(max_bars=2)

    assert result.orders
    assert result.trades
    assert result.final_state in {"NORMAL", "FREEZE_OPEN", "HALT"}

    events = [
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events[0]["written_at"] == "2024-01-02T15:00:00+08:00"
    assert all(event["written_at"].endswith("+08:00") for event in events)

    order = result.orders[0]
    assert order.created_at == datetime(2024, 1, 3, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert (tmp_path / "meta.db").exists()
    assert (tmp_path / "events.jsonl").exists()


def test_on_init_order_is_accepted_only_after_successful_startup_reconciliation(
    tmp_path,
    monkeypatch,
) -> None:
    strategy_module = ModuleType("tests.init_order_strategy")
    calls: list[str] = []

    class InitOrderStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            calls.append("on_init")
            ctx.order(
                "510300.SH",
                OrderSide.BUY,
                100,
                price=3.2,
                type=OrderType.LIMIT,
            )

        def on_start(self, ctx) -> None:
            calls.append("on_start")

        def on_bar(self, ctx, bar) -> None:
            return None

    strategy_module.InitOrderStrategy = InitOrderStrategy
    _install_strategy_module(monkeypatch, "tests.init_order_strategy", strategy_module)
    monkeypatch.setattr("quant.risk.pipeline.is_cn_continuous_auction", lambda _time: True)

    strategy_config = _paper_strategy_config(
        "tests.init_order_strategy:InitOrderStrategy",
        strategy_id="init_order_strategy",
    )
    paper_config = _paper_config(tmp_path)

    result = PaperEngine(strategy_config, paper_config).run_replay(max_bars=1)

    assert calls[:2] == ["on_init", "on_start"]
    assert result.orders
    assert result.final_state == EngineState.NORMAL.value
    events = _read_events(tmp_path / "events.jsonl")
    reconciliation_seq = next(
        event["seq"]
        for event in events
        if event["type"] == "reconciliation"
        and event["payload"]["startup"] is True
        and event["payload"]["status"] == "OK"
    )
    first_order_seq = next(event["seq"] for event in events if event["type"] == "order")
    assert reconciliation_seq < first_order_seq


def test_failed_startup_reconciliation_stops_before_on_init_orders(
    tmp_path,
    monkeypatch,
) -> None:
    strategy_module = ModuleType("tests.failed_startup_strategy")
    calls: list[str] = []

    class FailedStartupStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            calls.append("on_init")
            ctx.order(
                "510300.SH",
                OrderSide.BUY,
                100,
                price=3.2,
                type=OrderType.LIMIT,
            )

        def on_start(self, ctx) -> None:
            calls.append("on_start")

        def on_bar(self, ctx, bar) -> None:
            return None

    strategy_module.FailedStartupStrategy = FailedStartupStrategy
    _install_strategy_module(monkeypatch, "tests.failed_startup_strategy", strategy_module)
    monkeypatch.setattr("quant.risk.pipeline.is_cn_continuous_auction", lambda _time: True)

    strategy_config = _paper_strategy_config(
        "tests.failed_startup_strategy:FailedStartupStrategy",
        strategy_id="failed_startup_strategy",
    )
    paper_config = _paper_config(tmp_path)
    engine = PaperEngine(strategy_config, paper_config)
    engine.store.save_account_snapshot(
        Account("paper", "CNY", cash=50_000, frozen=0, market_value=0, total_value=50_000),
        {},
        datetime(2024, 1, 1, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    with pytest.raises(RuntimeError, match="startup reconciliation failed"):
        engine.run_replay(max_bars=1)

    assert calls == []
    assert engine.store.list_orders() == []
    assert engine.store.get_engine_state() == EngineState.HALT
    events = _read_events(tmp_path / "events.jsonl")
    assert events[-1]["type"] == "reconciliation"
    assert events[-1]["payload"]["startup"] is True
    assert events[-1]["payload"]["status"] == "FAILED"


def test_gateway_disconnect_through_paper_engine_freezes_and_emits_crit_alert(
    tmp_path,
    monkeypatch,
) -> None:
    strategy_module = ModuleType("tests.noop_paper_strategy")

    class NoopPaperStrategy(StrategyBase):
        def on_bar(self, ctx, bar) -> None:
            return None

    strategy_module.NoopPaperStrategy = NoopPaperStrategy
    _install_strategy_module(monkeypatch, "tests.noop_paper_strategy", strategy_module)
    strategy_config = _paper_strategy_config(
        "tests.noop_paper_strategy:NoopPaperStrategy",
        strategy_id="noop_paper_strategy",
    )
    paper_config = _paper_config(tmp_path)
    engine = PaperEngine(strategy_config, paper_config)
    engine.run_replay(max_bars=1)

    engine.gateway.inject_disconnect("network drill")

    assert engine.store.get_engine_state() == EngineState.FREEZE_OPEN
    events = _read_events(tmp_path / "events.jsonl")
    alert = next(
        event
        for event in reversed(events)
        if event["type"] == "alert" and event["payload"]["key"] == "gateway_disconnect"
    )
    assert alert["payload"]["severity"] == AlertSeverity.CRIT.value
    assert alert["payload"]["account_id"] == paper_config.account_id
    assert alert["payload"]["strategy_id"] == strategy_config.id
    assert alert["payload"]["payload"]["reason"] == "network drill"


def test_paper_engine_freezes_and_alerts_before_target_flush_when_daily_bar_missing(
    tmp_path,
    monkeypatch,
) -> None:
    strategy_module = ModuleType("tests.missing_daily_bar_strategy")

    class MissingDailyBarStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = "510300.SH"

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol:
                ctx.set_target(self.symbol, 1000)

    strategy_module.MissingDailyBarStrategy = MissingDailyBarStrategy
    _install_strategy_module(monkeypatch, "tests.missing_daily_bar_strategy", strategy_module)
    strategy_config = _paper_strategy_config(
        "tests.missing_daily_bar_strategy:MissingDailyBarStrategy",
        strategy_id="missing_daily_bar_strategy",
    ).model_copy(update={"universe": ["510300.SH", "000300.SH"]})
    paper_config = _paper_config(tmp_path)
    first_bar = DataService(Path("data_sample")).load_bars(["510300.SH"])[0]
    second_day_other_symbol = replace(
        first_bar,
        symbol="000300.SH",
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    engine = PaperEngine(strategy_config, paper_config)
    monkeypatch.setattr(
        engine.data,
        "load_bars",
        lambda _universe: [first_bar, second_day_other_symbol],
    )

    result = engine.run_replay()

    assert result.orders == []
    assert result.trades == []
    assert result.final_state == EngineState.FREEZE_OPEN.value
    events = _read_events(tmp_path / "events.jsonl")
    alert = next(
        event
        for event in events
        if event["type"] == "alert" and event["payload"]["key"] == "market_data_stale"
    )
    assert alert["payload"]["severity"] == AlertSeverity.CRIT.value
    assert alert["payload"]["account_id"] == paper_config.account_id
    assert alert["payload"]["strategy_id"] == strategy_config.id
    assert "last_bar_at" not in alert["payload"]["payload"]


def test_paper_engine_daily_replay_does_not_freeze_normal_target_flush(
    tmp_path,
    monkeypatch,
) -> None:
    strategy_module = ModuleType("tests.normal_daily_freshness_strategy")

    class NormalDailyFreshnessStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = "510300.SH"
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if not self.sent and bar.symbol == self.symbol:
                self.sent = True
                ctx.set_target(self.symbol, 1000)

    strategy_module.NormalDailyFreshnessStrategy = NormalDailyFreshnessStrategy
    _install_strategy_module(
        monkeypatch,
        "tests.normal_daily_freshness_strategy",
        strategy_module,
    )
    strategy_config = _paper_strategy_config(
        "tests.normal_daily_freshness_strategy:NormalDailyFreshnessStrategy",
        strategy_id="normal_daily_freshness_strategy",
    )
    paper_config = _paper_config(tmp_path)

    result = PaperEngine(strategy_config, paper_config).run_replay(max_bars=20)

    assert result.orders
    assert result.trades
    assert result.final_state == EngineState.NORMAL.value
    events = _read_events(tmp_path / "events.jsonl")
    assert not any(
        event["type"] == "alert" and event["payload"]["key"] == "market_data_stale"
        for event in events
    )


def test_paper_context_does_not_expose_runtime_internals(tmp_path) -> None:
    strategy_config = _paper_strategy_config(
        "strategies.dual_ma:DualMA",
        strategy_id="context_boundary_strategy",
    )
    paper_config = _paper_config(tmp_path)
    ctx = PaperEngine(strategy_config, paper_config).context

    for attr in ("engine", "gateway", "store", "oms"):
        assert not hasattr(ctx, attr)
        with pytest.raises(AttributeError):
            getattr(ctx, attr)


def test_paper_engine_refuses_non_paper_strategy(tmp_path) -> None:
    strategy_config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={"store_path": tmp_path / "meta.db", "events_path": tmp_path / "events.jsonl"}
    )

    with pytest.raises(ValueError, match="runtime_mode must be paper"):
        PaperEngine(strategy_config, paper_config)


def _install_strategy_module(monkeypatch, name: str, module: ModuleType) -> None:
    def fake_import_module(module_name: str):
        if module_name == name:
            return module
        return import_module(module_name)

    monkeypatch.setattr("quant.live.engine.import_module", fake_import_module)


def _paper_strategy_config(class_path: str, *, strategy_id: str):
    return load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml")).model_copy(
        update={
            "class_path": class_path,
            "params": {},
            "id": strategy_id,
        }
    )


def _paper_config(tmp_path):
    return load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )


def _read_events(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
