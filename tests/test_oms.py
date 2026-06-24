from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, OrderSide, OrderStatus, OrderType
from quant.live.events import EventJournal
from quant.live.oms import OrderManager
from quant.live.store import OmsStore
from quant.live.types import BrokerTradeSnapshot, EngineState
from quant.risk.pipeline import RiskEngine, RiskLimits


class FakeGateway:
    name = "fake"

    def __init__(self) -> None:
        self.sent = []
        self.cancelled = []

    def send_order(self, req):
        self.sent.append(req)
        return f"PAPER-{req.order_id}"

    def cancel_order(self, broker_order_id: str) -> None:
        self.cancelled.append(broker_order_id)

    def query_account(self):
        return Account("paper", "CNY", 100_000, 0, 0, 100_000)

    def query_positions(self):
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


def test_duplicate_broker_trade_is_idempotent(tmp_path) -> None:
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
    snap = BrokerTradeSnapshot(
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
    assert manager.on_broker_trade(snap) is not None
    assert manager.on_broker_trade(snap) is None
    assert len(manager.store.list_trades()) == 1
    assert manager.store.load_account_snapshot().account.cash == 100_000
