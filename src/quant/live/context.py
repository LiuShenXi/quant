from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

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


@dataclass(frozen=True)
class _PaperContextRuntime:
    account_id: str
    now: Callable[[], datetime]
    params: Callable[[], dict[str, Any]]
    history: Callable[..., pd.DataFrame]
    query_positions: Callable[[], dict[str, Position]]
    query_account: Callable[[], Account]
    list_open_orders: Callable[[], list[Order]]
    latest_price: Callable[[str], float]
    submit_order: Callable[..., str]
    set_target: Callable[..., None]
    cancel_order: Callable[[str], None]
    current_bar: Callable[[], Bar | None]
    get_instrument: Callable[[str], Instrument]
    schedule: Callable[[str, str], None]
    log: Callable[[str, str], None]
    save_kv: Callable[[str, object], None]
    load_kv: Callable[..., object | None]


class PaperContext(Context):
    __slots__ = ("_runtime", "strategy_id")

    def __init__(self, *, runtime: _PaperContextRuntime, strategy_id: str) -> None:
        self._runtime = runtime
        self.strategy_id = strategy_id

    @property
    def now(self) -> datetime:
        return self._runtime.now()

    @property
    def params(self) -> dict[str, Any]:
        return self._runtime.params()

    def history(
        self,
        symbol: str,
        n: int,
        freq: str = "1d",
        fields: Sequence[str] | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        return self._runtime.history(
            symbol,
            end=self.now,
            n=n,
            freq=freq,
            fields=fields,
            adjust=adjust,
        )

    def get_position(self, symbol: str) -> Position:
        position = self._runtime.query_positions().get(symbol)
        if position is not None:
            return position
        return Position(
            symbol=symbol,
            account_id=self._runtime.account_id,
            qty=0,
            sellable=0,
            avg_price=0,
            market_value=0,
        )

    def get_positions(self) -> dict[str, Position]:
        return self._runtime.query_positions()

    def get_account(self) -> Account:
        return self._runtime.query_account()

    def get_open_orders(self) -> list[Order]:
        return self._runtime.list_open_orders()

    def order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None = None,
        type: OrderType = OrderType.LIMIT,
    ) -> str:
        latest_price = self._runtime.latest_price(symbol)
        if latest_price <= 0 and price is not None:
            latest_price = price
        if latest_price <= 0:
            raise ValueError(f"no latest price available for {symbol}")
        return self._runtime.submit_order(
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
        self._runtime.set_target(
            strategy_id=self.strategy_id,
            symbol=symbol,
            target_qty=target_qty,
            now=self.now,
        )

    def cancel(self, order_id: str) -> None:
        self._runtime.cancel_order(order_id)

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None:
        bar = self._runtime.current_bar()
        if bar is None or bar.symbol != symbol or bar.freq != freq:
            return None
        return bar

    def get_instrument(self, symbol: str) -> Instrument:
        return self._runtime.get_instrument(symbol)

    def schedule(self, timer_id: str, at: str) -> None:
        self._runtime.schedule(timer_id, at)

    def log(self, msg: str, level: str = "INFO") -> None:
        self._runtime.log(msg, level)

    def save_state(self, key: str, value: Any) -> None:
        self._runtime.save_kv(self._state_key(key), value)

    def load_state(self, key: str, default: Any = None) -> Any:
        return self._runtime.load_kv(self._state_key(key), default=default)

    def _state_key(self, key: str) -> str:
        return f"strategy:{self.strategy_id}:{key}"
