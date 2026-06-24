from collections.abc import Callable

from quant.core.contract import Account, Bar, Order, Position, Trade
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, OrderRequest


class GatewayBase:
    def __init__(self) -> None:
        self.on_bar: Callable[[Bar], None] = lambda bar: None
        self.on_order: Callable[[Order], None] = lambda order: None
        self.on_trade: Callable[[Trade], None] = lambda trade: None
        self.on_disconnect: Callable[[str], None] = lambda reason: None

    def set_callbacks(
        self,
        *,
        on_bar: Callable[[Bar], None],
        on_order: Callable[[Order], None],
        on_trade: Callable[[Trade], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        self.on_bar = on_bar
        self.on_order = on_order
        self.on_trade = on_trade
        self.on_disconnect = on_disconnect

    def send_order(self, req: OrderRequest) -> str:
        raise NotImplementedError

    def cancel_order(self, broker_order_id: str) -> None:
        raise NotImplementedError

    def query_account(self) -> Account:
        raise NotImplementedError

    def query_positions(self) -> dict[str, Position]:
        raise NotImplementedError

    def query_orders(self, active_only: bool = True) -> list[BrokerOrderSnapshot]:
        raise NotImplementedError

    def query_trades(self) -> list[BrokerTradeSnapshot]:
        raise NotImplementedError
