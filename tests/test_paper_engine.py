from __future__ import annotations

import json
from datetime import datetime
from importlib import import_module
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

import pytest

from quant.core.config import load_strategy_config
from quant.core.contract import StrategyBase
from quant.data.service import DataService
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine


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


def test_paper_engine_refuses_non_paper_strategy(tmp_path) -> None:
    strategy_config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={"store_path": tmp_path / "meta.db", "events_path": tmp_path / "events.jsonl"}
    )

    with pytest.raises(ValueError, match="runtime_mode must be paper"):
        PaperEngine(strategy_config, paper_config)
