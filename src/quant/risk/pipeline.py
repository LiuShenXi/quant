from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from quant.core.contract import Account, Order, OrderSide, Position
from quant.live.types import EngineState, OrderRequest
from quant.risk.checks import is_cn_continuous_auction


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str | None = None
    rule_id: str | None = None


@dataclass(frozen=True)
class RiskLimits:
    universe: set[str]
    price_collar_pct: float = 0.02
    max_order_value: float = 200_000
    max_position_value_per_symbol: float = 500_000
    max_gross_exposure_pct: float = 0.95
    max_orders_per_minute: int = 10
    daily_loss_freeze_pct: float = 0.02
    daily_loss_halt_pct: float = 0.04


@dataclass
class RiskEngine:
    limits: RiskLimits
    day_start_value: float | None = None
    day: date | None = None
    order_timestamps: list[datetime] = field(default_factory=list)

    def check_order(
        self,
        req: OrderRequest,
        *,
        latest_price: float,
        account: Account,
        positions: dict[str, Position],
        active_orders: list[Order],
        now: datetime,
        state: EngineState,
    ) -> RiskDecision:
        try:
            return self._check_order(
                req,
                latest_price=latest_price,
                account=account,
                positions=positions,
                active_orders=active_orders,
                now=now,
                state=state,
            )
        except Exception as error:
            return RiskDecision(False, f"risk_engine_error: {error}", "risk_engine_error")

    def on_equity(self, total_value: float, now: datetime) -> EngineState | None:
        current_day = now.date()
        if self.day != current_day:
            self.day = current_day
            self.day_start_value = total_value
            return None

        if self.day_start_value is None:
            self.day_start_value = total_value
            return None

        if self.day_start_value <= 0:
            return EngineState.HALT

        loss_pct = (self.day_start_value - total_value) / self.day_start_value
        if loss_pct >= self.limits.daily_loss_halt_pct:
            return EngineState.HALT
        if loss_pct >= self.limits.daily_loss_freeze_pct:
            return EngineState.FREEZE_OPEN
        return None

    def _check_order(
        self,
        req: OrderRequest,
        *,
        latest_price: float,
        account: Account,
        positions: dict[str, Position],
        active_orders: list[Order],
        now: datetime,
        state: EngineState,
    ) -> RiskDecision:
        if state == EngineState.HALT:
            return _reject("engine is halted", "engine_state")
        if state == EngineState.FREEZE_OPEN and req.side == OrderSide.BUY:
            return _reject("engine freezes new opening orders", "engine_state")

        if req.symbol not in self.limits.universe:
            return _reject(f"symbol {req.symbol} is outside the risk universe", "symbol_whitelist")

        if not is_cn_continuous_auction(now.time()):
            return _reject("order is outside A-share continuous auction hours", "trading_session")

        if req.price is not None:
            if latest_price <= 0:
                return _reject("latest price must be positive for price collar", "price_collar")
            deviation = abs(req.price - latest_price) / latest_price
            if deviation > self.limits.price_collar_pct:
                return _reject("order price is outside the allowed collar", "price_collar")

        effective_price = req.price if req.price is not None else latest_price
        notional = req.qty * effective_price
        if req.qty <= 0 or effective_price <= 0:
            return _reject("order notional must be positive", "max_order_value")
        if notional > self.limits.max_order_value:
            return _reject("order value exceeds the single-order limit", "max_order_value")

        position = positions.get(req.symbol)
        if req.side == OrderSide.BUY:
            if notional > account.cash:
                return _reject("insufficient cash for buy order", "cash")
        else:
            sellable = position.sellable if position is not None else 0
            if req.qty > sellable:
                return _reject("insufficient sellable position for sell order", "cash")

        projected_symbol_value = _projected_symbol_value(req, notional, position)
        if projected_symbol_value > self.limits.max_position_value_per_symbol:
            return _reject("projected symbol position exceeds limit", "position_limit")

        projected_gross = _projected_gross_exposure(req, notional, positions)
        if account.total_value <= 0:
            return _reject("account total value must be positive", "gross_exposure")
        if projected_gross / account.total_value > self.limits.max_gross_exposure_pct:
            return _reject("projected gross exposure exceeds limit", "gross_exposure")

        self.order_timestamps = [
            timestamp
            for timestamp in self.order_timestamps
            if now - timestamp < timedelta(seconds=60)
        ]
        if len(self.order_timestamps) >= self.limits.max_orders_per_minute:
            return _reject("order frequency exceeds per-minute limit", "order_frequency")

        if _would_self_cross(req, active_orders):
            return _reject("order would self-cross with an active opposite order", "self_cross")

        self.order_timestamps.append(now)
        return RiskDecision(True)


def _reject(reason: str, rule_id: str) -> RiskDecision:
    return RiskDecision(False, reason, rule_id)


def _projected_symbol_value(
    req: OrderRequest,
    notional: float,
    position: Position | None,
) -> float:
    current_value = position.market_value if position is not None else 0
    if req.side == OrderSide.BUY:
        return current_value + notional
    return max(current_value - notional, 0)


def _projected_gross_exposure(
    req: OrderRequest,
    notional: float,
    positions: dict[str, Position],
) -> float:
    gross = sum(position.market_value for position in positions.values())
    current_value = positions[req.symbol].market_value if req.symbol in positions else 0
    projected_value = _projected_symbol_value(req, notional, positions.get(req.symbol))
    return gross - current_value + projected_value


def _would_self_cross(req: OrderRequest, active_orders: list[Order]) -> bool:
    for order in active_orders:
        if order.symbol != req.symbol or order.side == req.side:
            continue
        if req.price is None or order.price is None:
            return True
        if req.side == OrderSide.BUY and req.price >= order.price:
            return True
        if req.side == OrderSide.SELL and req.price <= order.price:
            return True
    return False
