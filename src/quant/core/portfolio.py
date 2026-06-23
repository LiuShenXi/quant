from dataclasses import dataclass

from quant.core.contract import Account, OrderSide, Position, Trade


@dataclass
class PositionState:
    qty: float = 0
    sellable: float = 0
    avg_price: float = 0


class Portfolio:
    def __init__(self, account_id: str, initial_cash: float) -> None:
        self.account_id = account_id
        self.cash = initial_cash
        self.frozen = 0.0
        self.positions: dict[str, PositionState] = {}

    def apply_trade(self, trade: Trade) -> None:
        state = self.positions.setdefault(trade.symbol, PositionState())
        value = trade.qty * trade.price
        if trade.side == OrderSide.BUY:
            old_cost = state.qty * state.avg_price
            state.qty += trade.qty
            state.avg_price = (old_cost + value) / state.qty
            self.cash -= value + trade.commission
        else:
            state.qty -= trade.qty
            state.sellable -= trade.qty
            self.cash += value - trade.commission

    def position(self, symbol: str, mark_price: float) -> Position:
        state = self.positions.get(symbol, PositionState())
        return Position(
            symbol=symbol,
            account_id=self.account_id,
            qty=state.qty,
            sellable=state.sellable,
            avg_price=state.avg_price,
            market_value=state.qty * mark_price,
        )

    def account(self, mark_prices: dict[str, float]) -> Account:
        market_value = sum(
            state.qty * mark_prices.get(symbol, state.avg_price)
            for symbol, state in self.positions.items()
        )
        return Account(
            account_id=self.account_id,
            currency="CNY",
            cash=round(self.cash, 2),
            frozen=round(self.frozen, 2),
            market_value=round(market_value, 2),
            total_value=round(self.cash + self.frozen + market_value, 2),
        )
