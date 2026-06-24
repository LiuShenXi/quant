from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant.core.contract import Bar, OrderSide, OrderStatus, OrderType
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
