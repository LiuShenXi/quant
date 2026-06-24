from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, OrderSide, OrderType, Position
from quant.live.types import EngineState, OrderRequest
from quant.risk.pipeline import RiskEngine, RiskLimits


def make_req(
    side: OrderSide = OrderSide.BUY,
    price: float = 3.2,
    qty: float = 1000,
) -> OrderRequest:
    return OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=side,
        type=OrderType.LIMIT,
        qty=qty,
        price=price,
        created_at=datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def make_account(cash: float = 100_000, total_value: float = 100_000) -> Account:
    return Account("paper", "CNY", cash=cash, frozen=0, market_value=0, total_value=total_value)


def test_risk_rejects_symbol_outside_universe() -> None:
    engine = RiskEngine(
        RiskLimits(
            universe={"159915.SZ"},
            price_collar_pct=0.02,
            max_order_value=200_000,
            max_position_value_per_symbol=500_000,
            max_gross_exposure_pct=0.95,
            max_orders_per_minute=10,
        )
    )
    decision = engine.check_order(
        make_req(),
        latest_price=3.2,
        account=make_account(),
        positions={},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.NORMAL,
    )
    assert decision.allowed is False
    assert decision.rule_id == "symbol_whitelist"


def test_freeze_open_blocks_buy_but_allows_sell() -> None:
    engine = RiskEngine(RiskLimits(universe={"510300.SH"}))
    sellable = Position(
        "510300.SH",
        "paper",
        qty=1000,
        sellable=1000,
        avg_price=3.0,
        market_value=3200,
    )

    buy = engine.check_order(
        make_req(OrderSide.BUY),
        latest_price=3.2,
        account=make_account(),
        positions={"510300.SH": sellable},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.FREEZE_OPEN,
    )
    sell = engine.check_order(
        make_req(OrderSide.SELL),
        latest_price=3.2,
        account=make_account(),
        positions={"510300.SH": sellable},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.FREEZE_OPEN,
    )
    assert buy.rule_id == "engine_state"
    assert sell.allowed is True


def test_daily_loss_moves_to_halt() -> None:
    engine = RiskEngine(
        RiskLimits(
            universe={"510300.SH"},
            daily_loss_freeze_pct=0.02,
            daily_loss_halt_pct=0.04,
        )
    )
    now = make_req().created_at
    assert engine.on_equity(100_000, now) is None
    assert engine.on_equity(95_000, now) == EngineState.HALT
