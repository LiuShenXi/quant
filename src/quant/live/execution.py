from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from quant.core.contract import OrderSide, OrderType, Position
from quant.live.oms import OrderManager


@dataclass(frozen=True)
class TargetIntent:
    strategy_id: str
    symbol: str
    target_qty: float
    created_at: datetime


class ExecutionRouter:
    def __init__(
        self,
        oms: OrderManager,
        position_getter: Callable[[], dict[str, Position]],
    ) -> None:
        self.oms = oms
        self._position_getter = position_getter
        self.pending_targets: list[TargetIntent] = []

    def set_target(
        self,
        *,
        strategy_id: str,
        symbol: str,
        target_qty: float,
        now: datetime,
    ) -> None:
        self.pending_targets.append(TargetIntent(strategy_id, symbol, target_qty, now))

    def flush_pending(self, *, now: datetime, latest_prices: dict[str, float]) -> list[str]:
        positions = self._position_getter()
        submitted: list[str] = []
        pending = self.pending_targets
        self.pending_targets = []
        for intent in pending:
            current_qty = positions.get(intent.symbol).qty if intent.symbol in positions else 0.0
            diff = intent.target_qty - current_qty
            if diff == 0:
                continue
            price = latest_prices[intent.symbol]
            submitted.append(
                self.oms.submit_order(
                    strategy_id=intent.strategy_id,
                    symbol=intent.symbol,
                    side=OrderSide.BUY if diff > 0 else OrderSide.SELL,
                    qty=abs(diff),
                    price=price,
                    type=OrderType.LIMIT,
                    latest_price=price,
                    now=now,
                )
            )
        return submitted
