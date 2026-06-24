import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant.core.contract import Account, OrderSide, OrderStatus, OrderType
from quant.live.events import EventJournal
from quant.live.oms import OrderManager
from quant.live.store import OmsStore
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, EngineState
from quant.risk.pipeline import RiskEngine, RiskLimits


class FakeGateway:
    name = "fake"

    def __init__(self) -> None:
        self.sent = []
        self.cancelled = []
        self.query_account_error: Exception | None = None
        self.query_positions_error: Exception | None = None
        self.cancel_error: Exception | None = None

    def send_order(self, req):
        self.sent.append(req)
        return f"PAPER-{req.order_id}"

    def cancel_order(self, broker_order_id: str) -> None:
        self.cancelled.append(broker_order_id)
        if self.cancel_error is not None:
            raise self.cancel_error

    def query_account(self):
        if self.query_account_error is not None:
            raise self.query_account_error
        return Account("paper", "CNY", 100_000, 0, 0, 100_000)

    def query_positions(self):
        if self.query_positions_error is not None:
            raise self.query_positions_error
        return {}

    def query_orders(self, active_only: bool = True):
        return []


def make_manager(tmp_path, universe: set[str] | None = None) -> OrderManager:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    risk_universe = {"510300.SH"} if universe is None else set(universe)
    return OrderManager(
        account_id="paper",
        gateway=FakeGateway(),
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        risk=RiskEngine(RiskLimits(universe=risk_universe)),
    )


def read_events(manager: OrderManager) -> list[dict]:
    return [
        json.loads(line)
        for line in manager.journal.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def submit_known_order(manager: OrderManager) -> str:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    return manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )


def make_trade_snapshot(order_id: str) -> BrokerTradeSnapshot:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    return BrokerTradeSnapshot(
        broker_trade_id="PAPER-T-1",
        broker_order_id="PAPER-O-1",
        order_id=order_id,
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=500,
        price=3.2,
        commission=5,
        dt=now,
    )


def test_submit_order_writes_before_gateway_send(tmp_path) -> None:
    manager = make_manager(tmp_path)
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )
    order = manager.store.get_order(order_id)
    assert order.status == OrderStatus.SUBMITTED
    assert order.broker_order_id == "PAPER-O-1"
    assert manager.gateway.sent[0].order_id == order_id


def test_risk_reject_creates_rejected_order_without_gateway_send(tmp_path) -> None:
    manager = make_manager(tmp_path, universe={"159915.SZ"})
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )
    order = manager.store.get_order(order_id)
    assert order.status == OrderStatus.REJECTED
    assert order.reject_reason.startswith("symbol_whitelist")
    assert manager.gateway.sent == []


def test_risk_engine_exception_freezes_open_without_gateway_send(tmp_path) -> None:
    manager = make_manager(tmp_path)

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    manager.risk._check_order = explode
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )

    order = manager.store.get_order(order_id)
    assert order.status == OrderStatus.REJECTED
    assert order.reject_reason.startswith("risk_engine_error")
    assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
    assert manager.gateway.sent == []


def test_unknown_broker_order_halts_and_audits_reconciliation_failure(tmp_path) -> None:
    manager = make_manager(tmp_path)
    now = datetime(2024, 1, 2, 9, 32, tzinfo=ZoneInfo("Asia/Shanghai"))
    snap = BrokerOrderSnapshot(
        broker_order_id="PAPER-O-404",
        order_id="O-404",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.2,
        status=OrderStatus.SUBMITTED,
        filled_qty=0,
        remaining_qty=1000,
        avg_fill_price=0,
        updated_at=now,
    )

    with pytest.raises(KeyError, match="O-404"):
        manager.on_broker_order(snap)

    assert manager.store.get_engine_state() == EngineState.HALT
    events = read_events(manager)
    assert events[-2]["type"] == "reconciliation"
    assert events[-2]["payload"] == {
        "kind": "broker_order",
        "order_id": "O-404",
        "broker_order_id": "PAPER-O-404",
        "status": "FAILED",
        "reason": "unknown_local_order: O-404",
    }
    assert events[-1]["type"] == "engine_state"
    assert events[-1]["payload"]["state"] == EngineState.HALT.value


def test_unknown_broker_trade_halts_and_does_not_persist_trade(tmp_path) -> None:
    manager = make_manager(tmp_path)
    snap = make_trade_snapshot("O-404")

    with pytest.raises(KeyError, match="O-404"):
        manager.on_broker_trade(snap)

    assert manager.store.list_trades() == []
    assert manager.store.get_engine_state() == EngineState.HALT
    events = read_events(manager)
    assert events[-2]["type"] == "reconciliation"
    assert events[-2]["payload"] == {
        "kind": "broker_trade",
        "order_id": "O-404",
        "broker_order_id": "PAPER-O-1",
        "broker_trade_id": "PAPER-T-1",
        "status": "FAILED",
        "reason": "unknown_local_order: O-404",
    }
    assert events[-1]["type"] == "engine_state"
    assert events[-1]["payload"]["state"] == EngineState.HALT.value


def test_freeze_open_preserves_existing_halt_and_audits_attempt(tmp_path) -> None:
    manager = make_manager(tmp_path)

    manager.halt("manual halt")
    manager.freeze_open("gateway issue")

    assert manager.store.get_engine_state() == EngineState.HALT
    events = read_events(manager)
    assert events[-1]["type"] == "engine_state"
    assert events[-1]["payload"] == {
        "state": EngineState.HALT.value,
        "reason": "gateway issue",
        "action": "preserve_halt",
        "requested_state": EngineState.FREEZE_OPEN.value,
    }


def test_trade_gateway_query_failure_freezes_open_and_audits_failure(tmp_path) -> None:
    manager = make_manager(tmp_path)
    order_id = submit_known_order(manager)
    manager.gateway.query_account_error = RuntimeError("account offline")
    snap = make_trade_snapshot(order_id)

    with pytest.raises(RuntimeError, match="account offline"):
        manager.on_broker_trade(snap)

    assert len(manager.store.list_trades()) == 1
    assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
    events = read_events(manager)
    assert events[-2]["type"] == "reconciliation"
    assert events[-2]["payload"] == {
        "kind": "broker_trade_snapshot_refresh",
        "order_id": order_id,
        "broker_order_id": "PAPER-O-1",
        "broker_trade_id": "PAPER-T-1",
        "status": "FAILED",
        "reason": "gateway_query_error: account offline",
    }
    assert events[-1]["type"] == "engine_state"
    assert events[-1]["payload"]["state"] == EngineState.FREEZE_OPEN.value


def test_cancel_failure_records_manual_op_and_freezes_open(tmp_path) -> None:
    manager = make_manager(tmp_path)
    order_id = submit_known_order(manager)
    manager.gateway.cancel_error = RuntimeError("cancel offline")

    with pytest.raises(RuntimeError, match="cancel offline"):
        manager.cancel_order(order_id)

    assert manager.gateway.cancelled == ["PAPER-O-1"]
    assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
    events = read_events(manager)
    assert events[-2]["type"] == "manual_ops"
    assert events[-2]["payload"] == {
        "action": "cancel_order",
        "order_id": order_id,
        "broker_order_id": "PAPER-O-1",
        "result": "failed",
        "reason": "gateway_cancel_error: cancel offline",
    }
    assert events[-1]["type"] == "engine_state"
    assert events[-1]["payload"]["state"] == EngineState.FREEZE_OPEN.value


def test_duplicate_broker_trade_is_idempotent(tmp_path) -> None:
    manager = make_manager(tmp_path)
    order_id = submit_known_order(manager)
    snap = make_trade_snapshot(order_id)
    assert manager.on_broker_trade(snap) is not None
    assert manager.on_broker_trade(snap) is None
    assert len(manager.store.list_trades()) == 1
    assert manager.store.load_account_snapshot().account.cash == 100_000
