from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

from quant.backtest.engine import BacktestEngine
from quant.backtest.events import EventJournal
from quant.backtest.results import write_result
from quant.core.config import RiskConfig, load_strategy_config
from quant.core.contract import OrderSide, OrderStatus, OrderType, StrategyBase
from quant.data.service import DataService


SCHEMA_KEYS = {
    "run_id",
    "seq",
    "event_type",
    "timestamp",
    "source_component",
    "strategy_id",
    "account_id",
    "symbol",
    "order_id",
    "trade_id",
    "risk_rule_id",
    "correlation_id",
    "payload",
}


def test_event_journal_records_required_schema() -> None:
    journal = EventJournal(run_id="run-001")
    timestamp = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))

    event = journal.append(
        "order_submitted",
        timestamp=timestamp,
        source_component="backtest.engine",
        payload={"side": "BUY"},
        strategy_id="strategy-001",
        account_id="backtest",
        symbol="510300.SH",
        order_id="O-1",
        correlation_id="target-1",
    )

    serialized = asdict(event)
    assert set(serialized) == SCHEMA_KEYS
    assert serialized["run_id"] == "run-001"
    assert serialized["seq"] == 1
    assert serialized["event_type"] == "order_submitted"
    assert serialized["timestamp"] == timestamp
    assert serialized["source_component"] == "backtest.engine"
    assert serialized["payload"] == {"side": "BUY"}


def test_event_journal_seq_is_monotonic_and_stable() -> None:
    journal = EventJournal(run_id="run-001")
    timestamp = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))

    first = journal.append(
        "engine_state",
        timestamp=timestamp,
        source_component="backtest.engine",
        payload={"state": "STARTED"},
    )
    second = journal.append(
        "target_intent",
        timestamp=timestamp,
        source_component="backtest.engine",
        payload={"target_qty": 100.0},
        symbol="510300.SH",
    )
    third = journal.append(
        "order_submitted",
        timestamp=timestamp,
        source_component="backtest.engine",
        payload={"qty": 100.0},
        order_id="O-1",
    )

    assert [event.seq for event in journal.events] == [1, 2, 3]
    assert [first.seq, second.seq, third.seq] == [1, 2, 3]
    assert first.seq == 1


def test_backtest_order_rejection_event_has_risk_rule_and_reason(monkeypatch) -> None:
    strategy_module = ModuleType("tests.backtest_journal_oversized_target_strategy")

    class OversizedTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target(self.symbol, self.target_qty)

    strategy_module.OversizedTargetStrategy = OversizedTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module
            if name == "tests.backtest_journal_oversized_target_strategy"
            else None
        ),
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_journal_oversized_target_strategy:OversizedTargetStrategy",
            "params": {"symbol": "510300.SH", "target_qty": 10_000},
            "risk": RiskConfig(max_position_value=5_000),
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    rejected_events = [event for event in result.events if event.event_type == "order_rejected"]
    assert len(rejected_events) == 1
    assert rejected_events[0].risk_rule_id == "position_limit"
    assert rejected_events[0].payload["reason"] == "projected symbol position exceeds limit"
    assert rejected_events[0].payload["status"] == "REJECTED"


def test_ctx_cancel_records_order_cancelled_event(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.backtest_journal_cancel_strategy")

    class CancelStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.cancelled = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.symbol or self.cancelled:
                return
            self.cancelled = True
            order_id = ctx.order(
                self.symbol,
                OrderSide.BUY,
                100,
                price=bar.close,
                type=OrderType.LIMIT,
            )
            ctx.cancel(order_id)

    strategy_module.CancelStrategy = CancelStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.backtest_journal_cancel_strategy" else None,
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_journal_cancel_strategy:CancelStrategy",
            "params": {"symbol": "510300.SH"},
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_cancel_data(tmp_path)),
        initial_cash=100_000,
    ).run()

    cancelled_events = [event for event in result.events if event.event_type == "order_cancelled"]
    assert len(cancelled_events) == 1
    event = cancelled_events[0]
    assert event.source_component == "backtest.engine"
    assert event.strategy_id == config.id
    assert event.account_id == "backtest"
    assert event.symbol == "510300.SH"
    assert event.order_id == "O-1"
    assert event.timestamp.isoformat() == "2024-01-02T10:00:00+08:00"
    assert event.payload["reason"] == "strategy_cancel_requested"
    assert event.payload["status"] == OrderStatus.CANCELLED.value
    assert result.orders[0].status == OrderStatus.CANCELLED
    assert result.trades == []


def test_result_export_writes_recorded_events_as_jsonl_objects(tmp_path) -> None:
    config = _active_sample_config()
    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    write_result(result, output_dir=tmp_path, config=config)

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    events = [json.loads(line) for line in lines]
    assert all(isinstance(event, dict) for event in events)
    assert all(set(event) == SCHEMA_KEYS for event in events)
    assert [event["seq"] for event in events] == sorted(event["seq"] for event in events)
    assert {event["event_type"] for event in events} >= {
        "engine_state",
        "target_intent",
        "order_submitted",
        "fill",
        "cash_transition",
    }


def _active_sample_config():
    return load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={"params": {"symbol": "510300.SH", "fast": 1, "slow": 2, "target_qty": 10000}}
    )


def _write_cancel_data(tmp_path: Path) -> Path:
    data_root = tmp_path / "cancel_data"
    data_root.mkdir()
    (data_root / "bars_1d.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,pre_close,limit_up,limit_down,suspended,data_status,source,updated_at",
                "510300.SH,2024-01-02T10:00:00+08:00,3.0,3.1,2.9,3.0,1000000,3000000,3.0,3.3,2.7,False,ok,test,2024-01-02T10:01:00+08:00",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "instruments.csv").write_text(
        "\n".join(
            [
                "symbol,name,type,exchange,list_date,delist_date,lot_size,qty_step,tick_size,t_plus,status",
                "510300.SH,CSI 300 ETF,etf,SH,2020-01-01,,100,100,0.001,1,active",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "adjust_factors.csv").write_text(
        "\n".join(
            [
                "symbol,ex_date,factor",
                "510300.SH,2024-01-02,1.0",
            ]
        ),
        encoding="utf-8",
    )
    return data_root
