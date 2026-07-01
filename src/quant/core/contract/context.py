from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

import pandas as pd

from quant.core.contract.types import (
    Account,
    Bar,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    Position,
)


class Context(Protocol):
    @property
    def now(self) -> datetime: ...

    @property
    def params(self) -> dict[str, Any]: ...

    def history(
        self,
        symbol: str,
        n: int,
        freq: str = "1d",
        fields: Sequence[str] | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame: ...

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None: ...

    def get_visible_bar_time(self, freq: str) -> datetime | None: ...

    def get_instrument(self, symbol: str) -> Instrument: ...

    def get_position(self, symbol: str) -> Position: ...

    def get_positions(self) -> dict[str, Position]: ...

    def get_account(self) -> Account: ...

    def get_open_orders(self) -> list[Order]: ...

    def order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None = None,
        type: OrderType = OrderType.LIMIT,
    ) -> str: ...

    def cancel(self, order_id: str) -> None: ...

    def set_target(self, symbol: str, target_qty: float) -> None: ...

    def schedule(self, timer_id: str, at: str) -> None: ...

    def log(self, msg: str, level: str = "INFO") -> None: ...

    def save_state(self, key: str, value: Any) -> None: ...

    def load_state(self, key: str, default: Any = None) -> Any: ...
