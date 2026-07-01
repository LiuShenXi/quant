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
from quant.core.contract import StrategyBase
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
