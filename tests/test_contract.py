from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, Bar, Order, OrderSide, OrderStatus, OrderType


def test_bar_requires_timezone_and_uses_bar_end_time() -> None:
    dt = datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    bar = Bar(
        symbol="510300.SH",
        freq="1d",
        dt=dt,
        open=3.5,
        high=3.6,
        low=3.4,
        close=3.55,
        volume=1000,
        amount=3550,
    )
    assert bar.dt == dt
    assert bar.freq == "1d"


def test_order_has_oms_fields() -> None:
    now = datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    order = Order(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="backtest",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.55,
        status=OrderStatus.SUBMITTED,
        filled_qty=0,
        remaining_qty=1000,
        avg_fill_price=0,
        created_at=now,
        updated_at=now,
    )
    assert order.broker_order_id is None
    assert order.reject_reason is None


def test_account_separates_cash_frozen_and_market_value() -> None:
    account = Account(
        account_id="backtest",
        currency="CNY",
        cash=100_000,
        frozen=0,
        market_value=0,
        total_value=100_000,
    )
    assert account.total_value == account.cash + account.frozen + account.market_value
