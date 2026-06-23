from datetime import datetime
from zoneinfo import ZoneInfo

from quant.backtest.matcher import Matcher
from quant.core.contract import Bar, Order, OrderSide, OrderStatus, OrderType


def make_order(side: OrderSide, price: float, qty: float = 1000) -> Order:
    now = datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    return Order(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="backtest",
        symbol="510300.SH",
        side=side,
        type=OrderType.LIMIT,
        qty=qty,
        price=price,
        status=OrderStatus.SUBMITTED,
        filled_qty=0,
        remaining_qty=qty,
        avg_fill_price=0,
        created_at=now,
        updated_at=now,
    )


def make_bar() -> Bar:
    return Bar(
        symbol="510300.SH",
        freq="1d",
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        open=3.00,
        high=3.10,
        low=2.95,
        close=3.05,
        volume=10_000,
        amount=30_500,
        limit_up=3.30,
        limit_down=2.70,
    )


def test_buy_limit_fills_when_limit_crosses_low() -> None:
    result = Matcher(volume_limit_pct=0.05).match(make_order(OrderSide.BUY, 3.00), make_bar())
    assert result.filled_qty == 500
    assert result.fill_price == 3.00


def test_buy_rejected_by_open_limit_up() -> None:
    bar = make_bar()
    locked = Bar(**{**bar.__dict__, "open": 3.30, "high": 3.30, "low": 3.30, "close": 3.30})
    result = Matcher(volume_limit_pct=0.05).match(make_order(OrderSide.BUY, 3.30), locked)
    assert result.filled_qty == 0
    assert result.reason == "open_limit_up"
