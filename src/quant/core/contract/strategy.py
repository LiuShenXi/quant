from abc import ABC, abstractmethod

from quant.core.contract.context import Context
from quant.core.contract.types import Bar, Order, Trade


class StrategyBase(ABC):
    def on_init(self, ctx: Context) -> None:
        return None

    def on_start(self, ctx: Context) -> None:
        return None

    @abstractmethod
    def on_bar(self, ctx: Context, bar: Bar) -> None:
        raise NotImplementedError

    def on_trade(self, ctx: Context, trade: Trade) -> None:
        return None

    def on_order(self, ctx: Context, order: Order) -> None:
        return None

    def on_timer(self, ctx: Context, timer_id: str) -> None:
        return None

    def on_stop(self, ctx: Context) -> None:
        return None
