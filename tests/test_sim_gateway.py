from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant.core.contract import (
    Account,
    Bar,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from quant.live.gateway.sim import SimGateway
from quant.live.types import OrderRequest


def make_bar() -> Bar:
    return Bar(
        symbol="510300.SH",
        freq="1d",
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        open=3.0,
        high=3.1,
        low=2.95,
        close=3.05,
        volume=10_000,
        amount=30_500,
        limit_up=3.3,
        limit_down=2.7,
    )


def make_req() -> OrderRequest:
    return OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.0,
        created_at=datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def make_order(
    *,
    order_id: str = "O-1",
    broker_order_id: str = "PAPER-O-7",
    status: OrderStatus = OrderStatus.SUBMITTED,
    filled_qty: float = 0,
    remaining_qty: float = 1000,
) -> Order:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    return Order(
        order_id=order_id,
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.0,
        status=status,
        filled_qty=filled_qty,
        remaining_qty=remaining_qty,
        avg_fill_price=3.0 if filled_qty else 0,
        created_at=now,
        updated_at=now,
        broker_order_id=broker_order_id,
    )


def test_sim_gateway_matches_partial_fill_and_updates_account() -> None:
    orders = []
    trades = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper", volume_limit_pct=0.05)
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=orders.append,
        on_trade=trades.append,
        on_disconnect=lambda reason: None,
    )

    broker_order_id = gateway.send_order(make_req())
    gateway.push_bar(make_bar())

    assert broker_order_id == "PAPER-O-1"
    assert orders[-1].status == OrderStatus.PARTIAL
    assert trades[0].broker_trade_id == "PAPER-T-1"
    assert trades[0].qty == 500
    assert gateway.query_account().cash < 100_000


def test_cancel_order_marks_cancelled() -> None:
    orders = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper")
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=orders.append,
        on_trade=lambda trade: None,
        on_disconnect=lambda reason: None,
    )

    broker_order_id = gateway.send_order(make_req())
    gateway.cancel_order(broker_order_id)

    assert orders[-1].status == OrderStatus.CANCELLED
    assert gateway.query_orders(active_only=True) == []


def test_disconnect_injection_blocks_send_and_emits_callback() -> None:
    disconnects = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper")
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=lambda order: None,
        on_trade=lambda trade: None,
        on_disconnect=disconnects.append,
    )

    gateway.inject_disconnect("network drill")
    with pytest.raises(ConnectionError, match="network drill"):
        gateway.send_order(make_req())

    assert disconnects == ["network drill"]
    gateway.reconnect()
    assert gateway.send_order(make_req()) == "PAPER-O-1"


def test_gateway_restores_snapshot_and_continues_active_orders() -> None:
    account = Account("paper", "CNY", cash=98_000, frozen=0, market_value=1_500, total_value=99_500)
    positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=500,
            sellable=0,
            avg_price=3.0,
            market_value=1_500,
        )
    }
    active_order = make_order()
    restored = SimGateway.from_snapshot(
        account=account,
        positions=positions,
        active_orders=[active_order],
        trades=[],
        account_id="paper",
        initial_cash=100_000,
        volume_limit_pct=0.05,
    )
    orders = []
    trades = []
    restored.set_callbacks(
        on_bar=lambda bar: None,
        on_order=orders.append,
        on_trade=trades.append,
        on_disconnect=lambda reason: None,
    )

    assert restored.query_account().cash == 98_000
    assert restored.query_positions()["510300.SH"].qty == 500
    assert restored.query_orders()[0].broker_order_id == "PAPER-O-7"

    restored.push_bar(make_bar())

    assert trades[0].broker_order_id == "PAPER-O-7"
    assert orders[-1].status == OrderStatus.PARTIAL
    assert restored.send_order(make_req()).startswith("PAPER-O-8")


def test_trade_callback_failure_does_not_leave_order_replayable() -> None:
    gateway = SimGateway(initial_cash=100_000, account_id="paper", volume_limit_pct=0.05)

    def fail_trade(_trade) -> None:
        raise RuntimeError("callback failed")

    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=lambda order: None,
        on_trade=fail_trade,
        on_disconnect=lambda reason: None,
    )
    gateway.send_order(
        OrderRequest(
            order_id="O-1",
            strategy_id="dual_ma_510300",
            account_id="paper",
            symbol="510300.SH",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            qty=500,
            price=3.0,
            created_at=datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
        )
    )

    with pytest.raises(RuntimeError, match="callback failed"):
        gateway.push_bar(make_bar())

    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=lambda order: None,
        on_trade=lambda trade: None,
        on_disconnect=lambda reason: None,
    )
    gateway.push_bar(make_bar())

    assert len(gateway.query_trades()) == 1


def test_mark_new_day_releases_pending_sellable() -> None:
    gateway = SimGateway(initial_cash=100_000, account_id="paper", volume_limit_pct=0.05)
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=lambda order: None,
        on_trade=lambda trade: None,
        on_disconnect=lambda reason: None,
    )
    gateway.send_order(make_req())
    gateway.push_bar(make_bar())

    assert gateway.query_positions()["510300.SH"].sellable == 0

    gateway.mark_new_day()

    assert gateway.query_positions()["510300.SH"].sellable == 500
