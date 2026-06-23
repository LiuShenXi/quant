from dataclasses import dataclass, replace
from datetime import datetime
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from quant.backtest.matcher import Matcher
from quant.core.config import StrategyConfig
from quant.core.contract import Bar, Order, OrderSide, OrderStatus, OrderType, StrategyBase, Trade
from quant.core.portfolio import Portfolio
from quant.costs import CostModel
from quant.data.quality import reject_missing_rows
from quant.data.service import DataService


@dataclass(frozen=True)
class BacktestResult:
    orders: list[Order]
    trades: list[Trade]
    equity: list[dict[str, object]]


class BacktestContext:
    def __init__(self, engine: "BacktestEngine") -> None:
        self.engine = engine

    @property
    def now(self) -> datetime:
        return self.engine.now

    @property
    def params(self) -> dict[str, Any]:
        return self.engine.config.params

    def history(
        self,
        symbol: str,
        n: int,
        freq: str = "1d",
        fields=None,
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

    def get_position(self, symbol: str):
        mark = self.engine.last_prices.get(symbol, 0.0)
        return self.engine.portfolio.position(symbol, mark_price=mark)

    def get_account(self):
        return self.engine.portfolio.account(self.engine.last_prices)

    def get_positions(self):
        return {
            symbol: self.engine.portfolio.position(symbol, mark)
            for symbol, mark in self.engine.last_prices.items()
        }

    def get_open_orders(self) -> list[Order]:
        return list(self.engine.open_orders)

    def order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None = None,
        type: OrderType = OrderType.LIMIT,
    ) -> str:
        return self.engine.submit_order(symbol=symbol, side=side, qty=qty, price=price, type=type)

    def set_target(self, symbol: str, target_qty: float) -> None:
        current = self.get_position(symbol).qty
        diff = target_qty - current
        if diff > 0:
            self.order(symbol, OrderSide.BUY, diff, price=self.engine.last_prices[symbol])
        elif diff < 0:
            self.order(symbol, OrderSide.SELL, -diff, price=self.engine.last_prices[symbol])

    def cancel(self, order_id: str) -> None:
        self.engine.cancel_order(order_id)

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None:
        return self.engine.current_bars.get(symbol)

    def get_instrument(self, symbol: str):
        return self.engine.data.get_instrument(symbol)

    def schedule(self, timer_id: str, at: str) -> None:
        return None

    def log(self, msg: str, level: str = "INFO") -> None:
        return None

    def save_state(self, key: str, value: Any) -> None:
        self.engine.state[key] = value

    def load_state(self, key: str, default: Any = None) -> Any:
        return self.engine.state.get(key, default)


class BacktestEngine:
    def __init__(self, config: StrategyConfig, data: DataService, initial_cash: float) -> None:
        self.config = config
        self.data = data
        self.now = datetime(1970, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.portfolio = Portfolio(account_id="backtest", initial_cash=initial_cash)
        self.matcher = Matcher(volume_limit_pct=0.05)
        self.cost_model = CostModel(
            commission_rate=0.00025,
            commission_min=5,
            stamp_tax=0,
            transfer_fee=0,
        )
        self.open_orders: list[Order] = []
        self.orders: list[Order] = []
        self.trades: list[Trade] = []
        self.equity: list[dict[str, object]] = []
        self.last_prices: dict[str, float] = {}
        self.current_bars: dict[str, Bar] = {}
        self.state: dict[str, object] = {}

    def run(self) -> BacktestResult:
        strategy = self._load_strategy()
        ctx = BacktestContext(self)
        strategy.on_init(ctx)
        strategy.on_start(ctx)
        bars = self._load_bars()
        for bar in bars:
            if self.now.date() != bar.dt.date():
                self.portfolio.mark_new_day()
            self.now = bar.dt
            self.current_bars[bar.symbol] = bar
            self.last_prices[bar.symbol] = bar.close
            self._match_open_orders(bar)
            strategy.on_bar(ctx, bar)
            self._record_equity()
        strategy.on_stop(ctx)
        return BacktestResult(orders=self.orders, trades=self.trades, equity=self.equity)

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None,
        type: OrderType,
    ) -> str:
        order_id = f"O-{len(self.orders) + 1}"
        order = Order(
            order_id=order_id,
            strategy_id=self.config.id,
            account_id="backtest",
            symbol=symbol,
            side=side,
            type=type,
            qty=qty,
            price=price,
            status=OrderStatus.SUBMITTED,
            filled_qty=0,
            remaining_qty=qty,
            avg_fill_price=0,
            created_at=self.now,
            updated_at=self.now,
        )
        self.orders.append(order)
        self.open_orders.append(order)
        return order_id

    def cancel_order(self, order_id: str) -> None:
        self.open_orders = [order for order in self.open_orders if order.order_id != order_id]

    def _load_strategy(self) -> StrategyBase:
        module_name, class_name = self.config.class_path.split(":")
        module = import_module(module_name)
        strategy_class = getattr(module, class_name)
        return strategy_class()

    def _load_bars(self) -> list[Bar]:
        rows = self.data._bars[self.data._bars["symbol"].isin(self.config.universe)].sort_values(
            ["dt", "symbol"]
        )
        reject_missing_rows(rows)
        return [
            Bar(
                symbol=row.symbol,
                freq="1d",
                dt=row.dt.to_pydatetime(),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                amount=float(row.amount),
                pre_close=float(row.pre_close),
                limit_up=float(row.limit_up),
                limit_down=float(row.limit_down),
                suspended=bool(row.suspended),
            )
            for row in rows.itertuples()
            if row.data_status == "ok"
        ]

    def _match_open_orders(self, bar: Bar) -> None:
        remaining: list[Order] = []
        for order in self.open_orders:
            result = self.matcher.match(order, bar)
            if result.filled_qty <= 0 or result.fill_price is None:
                remaining.append(order)
                continue
            commission = self.cost_model.calculate(order.side, result.filled_qty, result.fill_price)
            trade = Trade(
                trade_id=f"T-{len(self.trades) + 1}",
                order_id=order.order_id,
                strategy_id=order.strategy_id,
                account_id=order.account_id,
                symbol=order.symbol,
                side=order.side,
                qty=result.filled_qty,
                price=result.fill_price,
                commission=commission,
                dt=bar.dt,
            )
            self.trades.append(trade)
            self.portfolio.apply_trade(trade)
            remaining_qty = order.remaining_qty - result.filled_qty
            status = OrderStatus.FILLED if remaining_qty == 0 else OrderStatus.PARTIAL
            updated_order = replace(
                order,
                status=status,
                filled_qty=order.filled_qty + result.filled_qty,
                remaining_qty=remaining_qty,
                avg_fill_price=result.fill_price,
                updated_at=bar.dt,
            )
            self.orders = [
                updated_order if old.order_id == order.order_id else old for old in self.orders
            ]
            if remaining_qty > 0:
                remaining.append(updated_order)
        self.open_orders = remaining

    def _record_equity(self) -> None:
        account = self.portfolio.account(self.last_prices)
        self.equity.append(
            {"dt": self.now.isoformat(), "total_value": account.total_value, "cash": account.cash}
        )
