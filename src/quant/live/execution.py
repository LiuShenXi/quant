from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from quant.core.contract import OrderSide, OrderType, Position
from quant.core.sizing import split_qty_by_order_value
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
        max_order_value: float | None = None,
    ) -> None:
        self.oms = oms
        self._position_getter = position_getter
        self.max_order_value = max_order_value
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
        retained: list[TargetIntent] = []
        for intent in pending:
            current_qty = positions.get(intent.symbol).qty if intent.symbol in positions else 0.0
            diff = intent.target_qty - current_qty
            if diff == 0:
                continue
            price = latest_prices.get(intent.symbol)
            if price is None or price <= 0:
                retained.append(intent)
                self.oms.freeze_open(f"target_price_missing: {intent.symbol}")
                continue
            side = OrderSide.BUY if diff > 0 else OrderSide.SELL
            try:
                for qty in split_qty_by_order_value(
                    qty=abs(diff),
                    price=price,
                    max_order_value=self.max_order_value,
                ):
                    order_id = self.oms.submit_order(
                        strategy_id=intent.strategy_id,
                        symbol=intent.symbol,
                        side=side,
                        qty=qty,
                        price=price,
                        type=OrderType.LIMIT,
                        latest_price=price,
                        now=now,
                    )
                    submitted.append(order_id)
            except Exception as error:
                retained.append(intent)
                self.oms.freeze_open(f"target_submit_error: {error}")
                continue
        self.pending_targets = retained + self.pending_targets
        return submitted
