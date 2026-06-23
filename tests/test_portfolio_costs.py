from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import OrderSide, Trade
from quant.core.portfolio import Portfolio
from quant.costs import CostModel


def test_etf_buy_cost_uses_min_commission_and_no_stamp_tax() -> None:
    model = CostModel(commission_rate=0.00025, commission_min=5, stamp_tax=0, transfer_fee=0)
    assert model.calculate(OrderSide.BUY, qty=1000, price=3.0) == 5.0


def test_portfolio_buy_updates_cash_and_position() -> None:
    portfolio = Portfolio(account_id="backtest", initial_cash=100_000)
    trade = Trade(
        trade_id="T-1",
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="backtest",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.0,
        commission=5.0,
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    portfolio.apply_trade(trade)
    account = portfolio.account(mark_prices={"510300.SH": 3.0})
    position = portfolio.position("510300.SH", mark_price=3.0)
    assert account.cash == 96_995
    assert position.qty == 1000
    assert position.sellable == 0


def test_portfolio_rolls_bought_shares_to_sellable_next_day() -> None:
    portfolio = Portfolio(account_id="backtest", initial_cash=100_000)
    trade = Trade(
        trade_id="T-1",
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="backtest",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.0,
        commission=5.0,
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    portfolio.apply_trade(trade)
    portfolio.mark_new_day()
    assert portfolio.position("510300.SH", mark_price=3.0).sellable == 1000
