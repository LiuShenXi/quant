from dataclasses import replace

from quant.backtest.matcher import Matcher
from quant.core.contract import Account, Bar, Order, OrderStatus, Position, Trade
from quant.core.portfolio import Portfolio
from quant.costs import CostModel
from quant.live.gateway.base import GatewayBase
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, OrderRequest


class SimGateway(GatewayBase):
    name = "sim"

    def __init__(
        self,
        initial_cash: float,
        account_id: str,
        volume_limit_pct: float = 0.05,
    ) -> None:
        super().__init__()
        self.account_id = account_id
        self.connected = True
        self._disconnect_reason: str | None = None
        self._matcher = Matcher(volume_limit_pct=volume_limit_pct)
        self._portfolio = Portfolio(account_id=account_id, initial_cash=initial_cash)
        self._cost_model = CostModel(
            commission_rate=0.00025,
            commission_min=5,
            stamp_tax=0,
            transfer_fee=0,
        )
        self._next_order_seq = 1
        self._next_trade_seq = 1
        self._orders: dict[str, Order] = {}
        self._trades: list[Trade] = []
        self._last_prices: dict[str, float] = {}

    @classmethod
    def from_snapshot(
        cls,
        *,
        account: Account,
        positions: dict[str, Position],
        active_orders: list[Order],
        trades: list[Trade],
        account_id: str,
        initial_cash: float,
        volume_limit_pct: float = 0.05,
    ) -> "SimGateway":
        gateway = cls(
            initial_cash=initial_cash,
            account_id=account_id,
            volume_limit_pct=volume_limit_pct,
        )
        gateway._portfolio = Portfolio.from_snapshot(account, positions)
        gateway._orders = {
            order.broker_order_id: order
            for order in active_orders
            if order.broker_order_id is not None
        }
        gateway._trades = list(trades)
        gateway._last_prices = {
            symbol: _position_mark_price(position)
            for symbol, position in positions.items()
            if position.qty > 0
        }
        gateway._next_order_seq = _next_sequence(
            [order.broker_order_id for order in active_orders],
            prefix="PAPER-O-",
        )
        gateway._next_trade_seq = _next_sequence(
            [trade.broker_trade_id for trade in trades],
            prefix="PAPER-T-",
        )
        return gateway

    def send_order(self, req: OrderRequest) -> str:
        self._raise_if_disconnected()
        broker_order_id = f"PAPER-O-{self._next_order_seq}"
        self._next_order_seq += 1
        order = Order(
            order_id=req.order_id,
            strategy_id=req.strategy_id,
            account_id=req.account_id,
            symbol=req.symbol,
            side=req.side,
            type=req.type,
            qty=req.qty,
            price=req.price,
            status=OrderStatus.SUBMITTED,
            filled_qty=0,
            remaining_qty=req.qty,
            avg_fill_price=0,
            created_at=req.created_at,
            updated_at=req.created_at,
            broker_order_id=broker_order_id,
        )
        self._orders[broker_order_id] = order
        self.on_order(_order_snapshot(order))
        return broker_order_id

    def cancel_order(self, broker_order_id: str) -> None:
        self._raise_if_disconnected()
        order = self._orders[broker_order_id]
        if order.status not in {OrderStatus.SUBMITTED, OrderStatus.PARTIAL}:
            return
        cancelled = replace(
            order,
            status=OrderStatus.CANCELLED,
            updated_at=order.updated_at,
        )
        self._orders[broker_order_id] = cancelled
        self.on_order(_order_snapshot(cancelled))

    def push_bar(self, bar: Bar) -> None:
        self._last_prices[bar.symbol] = bar.close
        self.on_bar(bar)
        for broker_order_id, order in list(self._orders.items()):
            if order.symbol != bar.symbol or not _is_active(order):
                continue
            result = self._matcher.match(order, bar)
            if result.filled_qty <= 0 or result.fill_price is None:
                continue
            broker_trade_id = f"PAPER-T-{self._next_trade_seq}"
            self._next_trade_seq += 1
            commission = self._cost_model.calculate(
                order.side,
                result.filled_qty,
                result.fill_price,
            )
            trade = Trade(
                trade_id=broker_trade_id,
                order_id=order.order_id,
                strategy_id=order.strategy_id,
                account_id=order.account_id,
                symbol=order.symbol,
                side=order.side,
                qty=result.filled_qty,
                price=result.fill_price,
                commission=commission,
                dt=bar.dt,
                broker_order_id=broker_order_id,
                broker_trade_id=broker_trade_id,
            )
            updated = _apply_fill(order, result.filled_qty, result.fill_price, bar.dt)
            self._orders[broker_order_id] = updated
            self._trades.append(trade)
            self._portfolio.apply_trade(trade)
            self.on_trade(_trade_snapshot(trade))
            self.on_order(_order_snapshot(updated))

    def inject_disconnect(self, reason: str) -> None:
        self.connected = False
        self._disconnect_reason = reason
        self.on_disconnect(reason)

    def reconnect(self) -> None:
        self.connected = True
        self._disconnect_reason = None

    def mark_new_day(self) -> None:
        self._portfolio.mark_new_day()

    def query_account(self) -> Account:
        return self._portfolio.account(self._last_prices)

    def query_positions(self) -> dict[str, Position]:
        return {
            symbol: self._portfolio.position(symbol, mark_price)
            for symbol, mark_price in self._position_mark_prices().items()
        }

    def query_orders(self, active_only: bool = True) -> list[BrokerOrderSnapshot]:
        orders = [
            order
            for order in self._orders.values()
            if not active_only or _is_active(order)
        ]
        return [_order_snapshot(order) for order in orders]

    def query_trades(self) -> list[BrokerTradeSnapshot]:
        return [_trade_snapshot(trade) for trade in self._trades]

    def _position_mark_prices(self) -> dict[str, float]:
        return {
            symbol: self._last_prices.get(symbol, state.avg_price)
            for symbol, state in self._portfolio.positions.items()
        }

    def _raise_if_disconnected(self) -> None:
        if not self.connected:
            reason = self._disconnect_reason or "gateway disconnected"
            raise ConnectionError(reason)


def _is_active(order: Order) -> bool:
    return order.status in {OrderStatus.SUBMITTED, OrderStatus.PARTIAL}


def _apply_fill(order: Order, qty: float, price: float, updated_at) -> Order:
    filled_qty = order.filled_qty + qty
    remaining_qty = max(order.qty - filled_qty, 0)
    avg_fill_price = ((order.avg_fill_price * order.filled_qty) + (price * qty)) / filled_qty
    status = OrderStatus.FILLED if remaining_qty == 0 else OrderStatus.PARTIAL
    return replace(
        order,
        status=status,
        filled_qty=filled_qty,
        remaining_qty=remaining_qty,
        avg_fill_price=avg_fill_price,
        updated_at=updated_at,
    )


def _position_mark_price(position: Position) -> float:
    if position.qty == 0:
        return position.avg_price
    return position.market_value / position.qty if position.market_value > 0 else position.avg_price


def _next_sequence(values: list[str | None], prefix: str) -> int:
    seq = 1
    for value in values:
        if value is None or not value.startswith(prefix):
            continue
        try:
            seq = max(seq, int(value.removeprefix(prefix)) + 1)
        except ValueError:
            continue
    return seq


def _order_snapshot(order: Order) -> BrokerOrderSnapshot:
    if order.broker_order_id is None:
        raise ValueError("broker_order_id is required for broker order snapshots")
    return BrokerOrderSnapshot(
        broker_order_id=order.broker_order_id,
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        type=order.type,
        qty=order.qty,
        price=order.price,
        status=order.status,
        filled_qty=order.filled_qty,
        remaining_qty=order.remaining_qty,
        avg_fill_price=order.avg_fill_price,
        updated_at=order.updated_at,
    )


def _trade_snapshot(trade: Trade) -> BrokerTradeSnapshot:
    if trade.broker_order_id is None or trade.broker_trade_id is None:
        raise ValueError("broker IDs are required for broker trade snapshots")
    return BrokerTradeSnapshot(
        broker_trade_id=trade.broker_trade_id,
        broker_order_id=trade.broker_order_id,
        order_id=trade.order_id,
        strategy_id=trade.strategy_id,
        account_id=trade.account_id,
        symbol=trade.symbol,
        side=trade.side,
        qty=trade.qty,
        price=trade.price,
        commission=trade.commission,
        dt=trade.dt,
    )
