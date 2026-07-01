from dataclasses import dataclass, field

from quant.core.contract import Account, OrderSide, Position, Trade
from quant.core.settlement import SettlementRules


@dataclass
class PositionState:
    qty: float = 0
    sellable: float = 0
    pending_t0_sellable: float = 0
    pending_sellable: float = 0
    pending_sellable_by_lag: dict[int, float] = field(default_factory=dict)
    avg_price: float = 0


class Portfolio:
    def __init__(
        self,
        account_id: str,
        initial_cash: float,
        *,
        currency: str = "CNY",
        settlement: str | SettlementRules = "t1",
        allow_fractional: bool = False,
    ) -> None:
        self.account_id = account_id
        self.settlement_rules = (
            settlement
            if isinstance(settlement, SettlementRules)
            else SettlementRules(
                currency=currency,
                settlement=settlement,
                allow_fractional=allow_fractional,
            )
        )
        self.currency = self.settlement_rules.currency
        self.cash = initial_cash
        self.frozen = 0.0
        self.positions: dict[str, PositionState] = {}

    @classmethod
    def from_snapshot(
        cls,
        account: Account,
        positions: dict[str, Position],
    ) -> "Portfolio":
        portfolio = cls(
            account_id=account.account_id,
            initial_cash=account.cash,
            currency=account.currency,
        )
        portfolio.cash = account.cash
        portfolio.frozen = account.frozen
        portfolio.positions = {
            symbol: PositionState(
                qty=position.qty,
                sellable=position.sellable,
                pending_sellable=max(position.qty - position.sellable, 0),
                avg_price=position.avg_price,
            )
            for symbol, position in positions.items()
        }
        return portfolio

    def apply_trade(self, trade: Trade, *, instrument=None) -> None:
        state = self.positions.setdefault(trade.symbol, PositionState())
        value = trade.qty * trade.price
        if trade.side == OrderSide.BUY:
            old_cost = state.qty * state.avg_price
            state.qty = _clean_qty(state.qty + trade.qty)
            sellable_lag = self.settlement_rules.sellable_lag_bars(instrument)
            if sellable_lag <= 0:
                state.pending_t0_sellable = _clean_qty(state.pending_t0_sellable + trade.qty)
            elif sellable_lag == 1:
                state.pending_sellable = _clean_qty(state.pending_sellable + trade.qty)
            else:
                state.pending_sellable_by_lag[sellable_lag] = _clean_qty(
                    state.pending_sellable_by_lag.get(sellable_lag, 0.0) + trade.qty
                )
            state.avg_price = (old_cost + value) / state.qty if state.qty else 0
            self.cash -= value + trade.commission
        else:
            state.qty = _clean_qty(state.qty - trade.qty)
            state.sellable = _clean_qty(state.sellable - trade.qty)
            if state.qty == 0:
                state.avg_price = 0
            self.cash += value - trade.commission

    def mark_new_bar(self) -> None:
        for state in self.positions.values():
            state.sellable = _clean_qty(state.sellable + state.pending_t0_sellable)
            state.pending_t0_sellable = 0

    def mark_new_day(self) -> None:
        self.mark_new_bar()
        for state in self.positions.values():
            state.sellable = _clean_qty(state.sellable + state.pending_sellable)
            state.pending_sellable = 0
            if not state.pending_sellable_by_lag:
                continue
            pending_by_lag: dict[int, float] = {}
            released = 0.0
            for lag, qty in state.pending_sellable_by_lag.items():
                remaining_lag = lag - 1
                if remaining_lag <= 0:
                    released += qty
                else:
                    pending_by_lag[remaining_lag] = _clean_qty(
                        pending_by_lag.get(remaining_lag, 0.0) + qty
                    )
            state.sellable = _clean_qty(state.sellable + released)
            state.pending_sellable_by_lag = pending_by_lag

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
            currency=self.currency,
            cash=round(self.cash, 2),
            frozen=round(self.frozen, 2),
            market_value=round(market_value, 2),
            total_value=round(self.cash + self.frozen + market_value, 2),
        )


def _clean_qty(value: float) -> float:
    rounded = round(value, 12)
    return 0.0 if abs(rounded) < 1e-12 else rounded
