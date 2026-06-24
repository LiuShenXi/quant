from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from quant.core.contract import (
    Account,
    Bar,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    Position,
)
from quant.core.contract.context import Context

if TYPE_CHECKING:
    from quant.live.engine import PaperEngine


class PaperContext(Context):
    def __init__(self, engine: PaperEngine, strategy_id: str) -> None:
        self.engine = engine
        self.strategy_id = strategy_id

    @property
    def now(self) -> datetime:
        return self.engine.now

    @property
    def params(self) -> dict[str, Any]:
        return self.engine.strategy_config.params

    def history(
        self,
        symbol: str,
        n: int,
        freq: str = "1d",
        fields: Sequence[str] | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        return self.engine.data.history(
            symbol,
            end=self.now,
            n=n,
            freq=freq,
            fields=fields,
            adjust=adjust,
        )

    def get_position(self, symbol: str) -> Position:
        position = self.engine.gateway.query_positions().get(symbol)
        if position is not None:
            return position
        return Position(
            symbol=symbol,
            account_id=self.engine.paper_config.account_id,
            qty=0,
            sellable=0,
            avg_price=0,
            market_value=0,
        )

    def get_positions(self) -> dict[str, Position]:
        return self.engine.gateway.query_positions()

    def get_account(self) -> Account:
        return self.engine.gateway.query_account()

    def get_open_orders(self) -> list[Order]:
        return self.engine.oms.store.list_orders(active_only=True)

    def order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None = None,
        type: OrderType = OrderType.LIMIT,
    ) -> str:
        latest_price = self.engine.latest_price(symbol)
        if latest_price <= 0 and price is not None:
            latest_price = price
        if latest_price <= 0:
            raise ValueError(f"no latest price available for {symbol}")
        return self.engine.oms.submit_order(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            type=type,
            latest_price=latest_price,
            now=self.now,
        )

    def set_target(self, symbol: str, target_qty: float) -> None:
        self.engine.execution_router.set_target(
            strategy_id=self.strategy_id,
            symbol=symbol,
            target_qty=target_qty,
            now=self.now,
        )

    def cancel(self, order_id: str) -> None:
        self.engine.oms.cancel_order(order_id)

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None:
        bar = self.engine.current_bar
        if bar is None or bar.symbol != symbol or bar.freq != freq:
            return None
        return bar

    def get_instrument(self, symbol: str) -> Instrument:
        return self.engine.data.get_instrument(symbol)

    def schedule(self, timer_id: str, at: str) -> None:
        self.engine.state["timers"][timer_id] = at

    def log(self, msg: str, level: str = "INFO") -> None:
        self.engine.state["logs"].append(
            {"level": level, "message": msg, "at": self.now.isoformat()}
        )

    def save_state(self, key: str, value: Any) -> None:
        self.engine.store.save_kv(self._state_key(key), value)

    def load_state(self, key: str, default: Any = None) -> Any:
        return self.engine.store.load_kv(self._state_key(key), default=default)

    def _state_key(self, key: str) -> str:
        return f"strategy:{self.strategy_id}:{key}"
