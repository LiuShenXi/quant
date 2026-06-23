from dataclasses import dataclass

from quant.core.contract import Bar, Order, OrderSide


@dataclass(frozen=True)
class MatchResult:
    filled_qty: float
    fill_price: float | None
    reason: str | None = None


class Matcher:
    def __init__(self, volume_limit_pct: float) -> None:
        self.volume_limit_pct = volume_limit_pct

    def match(self, order: Order, bar: Bar) -> MatchResult:
        if bar.suspended:
            return MatchResult(0, None, "suspended")
        if order.side == OrderSide.BUY and bar.limit_up is not None and bar.open >= bar.limit_up:
            return MatchResult(0, None, "open_limit_up")
        if (
            order.side == OrderSide.SELL
            and bar.limit_down is not None
            and bar.open <= bar.limit_down
        ):
            return MatchResult(0, None, "open_limit_down")
        if order.price is None:
            fill_price = bar.open
        elif order.side == OrderSide.BUY and order.price >= bar.low:
            fill_price = min(order.price, bar.open)
        elif order.side == OrderSide.SELL and order.price <= bar.high:
            fill_price = max(order.price, bar.open)
        else:
            return MatchResult(0, None, "not_touched")
        volume_cap = bar.volume * self.volume_limit_pct
        filled_qty = min(order.remaining_qty, volume_cap)
        return MatchResult(filled_qty=filled_qty, fill_price=fill_price)
