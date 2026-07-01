from dataclasses import dataclass, field, replace
from datetime import datetime, time
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from quant.backtest.clock import BacktestClock
from quant.backtest.events import EventJournal, JournalEvent
from quant.backtest.matcher import Matcher
from quant.core.config import StrategyConfig
from quant.core.contract import (
    Bar,
    EngineState,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    StrategyBase,
    Trade,
)
from quant.core.portfolio import Portfolio
from quant.core.sizing import split_qty_by_order_value
from quant.costs import CostModel
from quant.data.service import DataService
from quant.risk.pipeline import RiskEngine, RiskLimits


@dataclass(frozen=True)
class BacktestResult:
    orders: list[Order]
    trades: list[Trade]
    equity: list[dict[str, object]]
    events: list[JournalEvent] = field(default_factory=list)


@dataclass(frozen=True)
class TargetIntent:
    strategy_id: str
    symbol: str
    target_qty: float
    created_at: datetime
    correlation_id: str


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
        if not self.engine.has_frequency(freq):
            return self.engine.data.history(
                symbol,
                end=self.now,
                n=n,
                freq=freq,
                fields=fields,
                adjust=adjust,
            )
        end = self.engine.get_visible_bar_time(freq)
        if end is None:
            return _empty_history(fields)
        return self.engine.data.history(
            symbol,
            end=end,
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
        self.engine.set_target(symbol=symbol, target_qty=target_qty)

    def cancel(self, order_id: str) -> None:
        self.engine.cancel_order(order_id)

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None:
        return self.engine.current_bars_by_frequency.get(freq, {}).get(symbol)

    def get_visible_bar_time(self, freq: str) -> datetime | None:
        return self.engine.get_visible_bar_time(freq)

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
    def __init__(
        self,
        config: StrategyConfig,
        data: DataService,
        initial_cash: float,
        run_id: str | None = None,
    ) -> None:
        self.config = config
        self.data = data
        self.run_id = run_id or config.id
        self.journal = EventJournal(run_id=self.run_id)
        self.now = datetime(1970, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.portfolio = Portfolio(account_id="backtest", initial_cash=initial_cash)
        self.matcher = Matcher(volume_limit_pct=0.05)
        self.risk = RiskEngine(self._build_risk_limits())
        self.cost_model = CostModel(
            commission_rate=0.00025,
            commission_min=5,
            stamp_tax=0,
            transfer_fee=0,
        )
        self.open_orders: list[Order] = []
        self.order_correlation_ids: dict[str, str | None] = {}
        self.pending_targets: list[TargetIntent] = []
        self.orders: list[Order] = []
        self.trades: list[Trade] = []
        self.equity: list[dict[str, object]] = []
        self.last_prices: dict[str, float] = {}
        self.current_bars: dict[str, Bar] = {}
        self.current_bars_by_frequency: dict[str, dict[str, Bar]] = {}
        self.visible_bar_times: dict[str, datetime | None] = {}
        self.loaded_frequencies: set[str] = set()
        self.clock: BacktestClock | None = None
        self.state: dict[str, object] = {}
        self._target_seq = 0

    def run(self) -> BacktestResult:
        self._append_event(
            "engine_state",
            payload={"state": "STARTED"},
        )
        strategy = self._load_strategy()
        ctx = BacktestContext(self)
        strategy.on_init(ctx)
        strategy.on_start(ctx)
        bars_by_frequency = self._load_bars_by_frequency()
        self.loaded_frequencies = set(bars_by_frequency)
        self.clock = BacktestClock(
            bars_by_frequency=bars_by_frequency,
            primary_frequency=self.config.primary_frequency,
        )
        if self.config.primary_frequency == "1d":
            self._run_daily_sessions(strategy, ctx, bars_by_frequency)
        else:
            self._run_primary_timeline(strategy, ctx, bars_by_frequency)
        strategy.on_stop(ctx)
        self._append_event(
            "engine_state",
            payload={"state": "STOPPED"},
        )
        return BacktestResult(
            orders=self.orders,
            trades=self.trades,
            equity=self.equity,
            events=list(self.journal.events),
        )

    def _run_daily_sessions(
        self,
        strategy: StrategyBase,
        ctx: BacktestContext,
        bars_by_frequency: dict[str, list[Bar]],
    ) -> None:
        bars = bars_by_frequency[self.config.primary_frequency]
        for day_bars in _group_bars_by_session(bars):
            first_bar = day_bars[0]
            if self.now.date() != first_bar.dt.date():
                self.portfolio.mark_new_day()
            self.now = _continuous_auction_open(first_bar.dt)
            open_prices = {bar.symbol: bar.open for bar in day_bars}
            self.last_prices.update(open_prices)
            self._flush_pending_targets(open_prices)
            for bar in day_bars:
                self._match_open_orders(bar)

            self.current_bars.update({bar.symbol: bar for bar in day_bars})
            close_prices = {bar.symbol: bar.close for bar in day_bars}
            self.last_prices.update(close_prices)
            self._set_visible_bars(first_bar.dt, bars_by_frequency)
            for bar in day_bars:
                self.now = bar.dt
                strategy.on_bar(ctx, bar)
            self._record_equity()

    def _run_primary_timeline(
        self,
        strategy: StrategyBase,
        ctx: BacktestContext,
        bars_by_frequency: dict[str, list[Bar]],
    ) -> None:
        primary_frequency = self.config.primary_frequency
        primary_bars_by_time = _index_bars_by_time(bars_by_frequency[primary_frequency])
        if self.clock is None:
            raise RuntimeError("backtest clock is not initialized")
        for decision_time in self.clock.primary_timeline():
            if self.now.date() != decision_time.date():
                self.portfolio.mark_new_day()
            self.now = decision_time
            primary_bars = primary_bars_by_time[decision_time]
            open_prices = {bar.symbol: bar.open for bar in primary_bars}
            self.last_prices.update(open_prices)
            self._flush_pending_targets(open_prices)
            for bar in primary_bars:
                self._match_open_orders(bar)

            self._set_visible_bars(decision_time, bars_by_frequency)
            close_prices = {bar.symbol: bar.close for bar in primary_bars}
            self.last_prices.update(close_prices)
            for bar in primary_bars:
                strategy.on_bar(ctx, bar)
            self._record_equity()

    def set_target(self, *, symbol: str, target_qty: float) -> None:
        self._target_seq += 1
        correlation_id = f"target-{self._target_seq}"
        self.pending_targets.append(
            TargetIntent(
                strategy_id=self.config.id,
                symbol=symbol,
                target_qty=target_qty,
                created_at=self.now,
                correlation_id=correlation_id,
            )
        )
        self._append_event(
            "target_intent",
            symbol=symbol,
            correlation_id=correlation_id,
            payload={"target_qty": target_qty},
        )

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None,
        type: OrderType,
        *,
        now: datetime | None = None,
        latest_price: float | None = None,
        correlation_id: str | None = None,
    ) -> str:
        order_id = f"O-{len(self.orders) + 1}"
        created_at = now or self.now
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
            created_at=created_at,
            updated_at=created_at,
        )
        self.order_correlation_ids[order_id] = correlation_id
        decision = self.risk.check_order(
            OrderRequest(
                order_id=order_id,
                strategy_id=self.config.id,
                account_id="backtest",
                symbol=symbol,
                side=side,
                type=type,
                qty=qty,
                price=price,
                created_at=created_at,
            ),
            latest_price=(
                latest_price if latest_price is not None else self.last_prices.get(symbol, 0)
            ),
            account=self.portfolio.account(self.last_prices),
            positions={
                position_symbol: self.portfolio.position(position_symbol, mark)
                for position_symbol, mark in self._position_mark_prices().items()
            },
            active_orders=self.open_orders,
            now=created_at,
            state=EngineState.NORMAL,
        )
        self._append_event(
            "risk_check",
            timestamp=created_at,
            symbol=symbol,
            order_id=order_id,
            risk_rule_id=decision.rule_id,
            correlation_id=correlation_id,
            payload={
                "allowed": decision.allowed,
                "reason": decision.reason,
                "side": side.value,
                "type": type.value,
                "qty": qty,
                "price": price,
            },
        )
        if not decision.allowed:
            rejected = replace(
                order,
                status=OrderStatus.REJECTED,
                reject_reason=_risk_reject_reason(decision.rule_id, decision.reason),
            )
            self.orders.append(rejected)
            self._append_event(
                "order_rejected",
                timestamp=created_at,
                symbol=symbol,
                order_id=order_id,
                risk_rule_id=decision.rule_id,
                correlation_id=correlation_id,
                payload={
                    "side": side.value,
                    "type": type.value,
                    "qty": qty,
                    "price": price,
                    "status": OrderStatus.REJECTED.value,
                    "reason": decision.reason,
                    "reject_reason": rejected.reject_reason,
                },
            )
            return order_id
        self.orders.append(order)
        self.open_orders.append(order)
        self._append_event(
            "order_submitted",
            timestamp=created_at,
            symbol=symbol,
            order_id=order_id,
            correlation_id=correlation_id,
            payload={
                "side": side.value,
                "type": type.value,
                "qty": qty,
                "price": price,
                "status": OrderStatus.SUBMITTED.value,
            },
        )
        return order_id

    def cancel_order(self, order_id: str) -> None:
        self.open_orders = [order for order in self.open_orders if order.order_id != order_id]

    def get_visible_bar_time(self, freq: str) -> datetime | None:
        if freq in self.visible_bar_times:
            return self.visible_bar_times[freq]
        if self.clock is None:
            return None
        return self.clock.visible_bar_time(freq, self.now)

    def has_frequency(self, freq: str) -> bool:
        return freq in self.loaded_frequencies

    def _flush_pending_targets(self, latest_prices: dict[str, float]) -> None:
        pending = self.pending_targets
        self.pending_targets = []
        retained: list[TargetIntent] = []
        for intent in pending:
            price = latest_prices.get(intent.symbol)
            if price is None or price <= 0:
                self._append_event(
                    "rebalance_decision",
                    symbol=intent.symbol,
                    correlation_id=intent.correlation_id,
                    payload={
                        "target_qty": intent.target_qty,
                        "action": "retained",
                        "reason": "missing_latest_price",
                    },
                )
                retained.append(intent)
                continue
            current = self._effective_target_qty(intent.symbol)
            diff = intent.target_qty - current
            self._append_event(
                "rebalance_decision",
                symbol=intent.symbol,
                correlation_id=intent.correlation_id,
                payload={
                    "target_qty": intent.target_qty,
                    "current_qty": current,
                    "diff_qty": diff,
                    "price": price,
                    "action": "noop" if diff == 0 else "submit_order",
                },
            )
            if diff == 0:
                continue
            side = OrderSide.BUY if diff > 0 else OrderSide.SELL
            for qty in split_qty_by_order_value(
                qty=abs(diff),
                price=price,
                max_order_value=self.risk.limits.max_order_value,
            ):
                self.submit_order(
                    symbol=intent.symbol,
                    side=side,
                    qty=qty,
                    price=price,
                    type=OrderType.LIMIT,
                    now=self.now,
                    latest_price=price,
                    correlation_id=intent.correlation_id,
                )
        self.pending_targets = retained + self.pending_targets

    def _effective_target_qty(self, symbol: str) -> float:
        mark = self.last_prices.get(symbol, 0.0)
        qty = self.portfolio.position(symbol, mark_price=mark).qty
        for order in self.open_orders:
            if order.symbol != symbol:
                continue
            if order.side == OrderSide.BUY:
                qty += order.remaining_qty
            else:
                qty -= order.remaining_qty
        return qty

    def _position_mark_prices(self) -> dict[str, float]:
        return {
            symbol: self.last_prices.get(symbol, state.avg_price)
            for symbol, state in self.portfolio.positions.items()
        }

    def _load_strategy(self) -> StrategyBase:
        module_name, class_name = self.config.class_path.split(":")
        module = import_module(module_name)
        strategy_class = getattr(module, class_name)
        return strategy_class()

    def _load_bars_by_frequency(self) -> dict[str, list[Bar]]:
        frequencies = _unique_frequencies(
            [self.config.primary_frequency, *self.config.history_frequencies]
        )
        return {
            freq: self.data.load_bars(self.config.universe, freq=freq)
            for freq in frequencies
        }

    def _load_bars(self) -> list[Bar]:
        return self.data.load_bars(self.config.universe, freq=self.config.primary_frequency)

    def _match_open_orders(self, bar: Bar) -> None:
        remaining: list[Order] = []
        for order in self.open_orders:
            if order.symbol != bar.symbol:
                remaining.append(order)
                continue
            result = self.matcher.match(order, bar)
            if result.filled_qty <= 0 or result.fill_price is None:
                remaining.append(order)
                continue
            commission = self.cost_model.calculate(order.side, result.filled_qty, result.fill_price)
            cash_before = self.portfolio.account(self.last_prices).cash
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
            cash_after = self.portfolio.account(self.last_prices).cash
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
            correlation_id = self.order_correlation_ids.get(order.order_id)
            self._append_event(
                "fill",
                timestamp=bar.dt,
                symbol=order.symbol,
                order_id=order.order_id,
                trade_id=trade.trade_id,
                correlation_id=correlation_id,
                payload={
                    "side": order.side.value,
                    "qty": result.filled_qty,
                    "price": result.fill_price,
                    "commission": commission,
                    "order_status": status.value,
                    "remaining_qty": remaining_qty,
                },
            )
            self._append_event(
                "cash_transition",
                timestamp=bar.dt,
                symbol=order.symbol,
                order_id=order.order_id,
                trade_id=trade.trade_id,
                correlation_id=correlation_id,
                payload={
                    "cash_before": cash_before,
                    "cash_after": cash_after,
                    "delta": round(cash_after - cash_before, 2),
                },
            )
            if remaining_qty > 0:
                remaining.append(updated_order)
        self.open_orders = remaining

    def _record_equity(self) -> None:
        account = self.portfolio.account(self.last_prices)
        self.equity.append(
            {"dt": self.now.isoformat(), "total_value": account.total_value, "cash": account.cash}
        )

    def _set_visible_bars(
        self,
        decision_time: datetime,
        bars_by_frequency: dict[str, list[Bar]],
    ) -> None:
        if self.clock is None:
            raise RuntimeError("backtest clock is not initialized")
        self.visible_bar_times = {
            freq: self.clock.visible_bar_time(freq, decision_time)
            for freq in bars_by_frequency
        }
        self.current_bars_by_frequency = {}
        for freq, bars in bars_by_frequency.items():
            visible_time = self.visible_bar_times[freq]
            self.current_bars_by_frequency[freq] = {
                bar.symbol: bar for bar in bars if visible_time is not None and bar.dt == visible_time
            }
        self.current_bars = self.current_bars_by_frequency.get(self.config.primary_frequency, {})

    def _append_event(
        self,
        event_type: str,
        *,
        timestamp: datetime | None = None,
        source_component: str = "backtest.engine",
        payload: dict[str, Any] | None = None,
        strategy_id: str | None = None,
        account_id: str | None = None,
        symbol: str | None = None,
        order_id: str | None = None,
        trade_id: str | None = None,
        risk_rule_id: str | None = None,
        correlation_id: str | None = None,
    ) -> JournalEvent:
        return self.journal.append(
            event_type,
            timestamp=timestamp or self.now,
            source_component=source_component,
            payload=payload or {},
            strategy_id=strategy_id or self.config.id,
            account_id=account_id or "backtest",
            symbol=symbol,
            order_id=order_id,
            trade_id=trade_id,
            risk_rule_id=risk_rule_id,
            correlation_id=correlation_id,
        )

    def _build_risk_limits(self) -> RiskLimits:
        risk = self.config.risk
        return RiskLimits(
            universe=set(self.config.universe),
            max_order_value=risk.max_order_value if risk.max_order_value is not None else 200_000,
            max_position_value_per_symbol=(
                risk.max_position_value if risk.max_position_value is not None else 500_000
            ),
            max_gross_exposure_pct=(
                risk.max_gross_exposure_pct if risk.max_gross_exposure_pct is not None else 0.95
            ),
            max_orders_per_minute=(
                risk.max_orders_per_minute if risk.max_orders_per_minute is not None else 10
            ),
        )


def _continuous_auction_open(value: datetime) -> datetime:
    return datetime.combine(
        value.date(),
        time(9, 31),
        tzinfo=value.tzinfo or ZoneInfo("Asia/Shanghai"),
    )


def _group_bars_by_session(bars: list[Bar]) -> list[list[Bar]]:
    sessions: list[list[Bar]] = []
    for bar in bars:
        if not sessions or sessions[-1][0].dt.date() != bar.dt.date():
            sessions.append([bar])
            continue
        sessions[-1].append(bar)
    return sessions


def _index_bars_by_time(bars: list[Bar]) -> dict[datetime, list[Bar]]:
    indexed: dict[datetime, list[Bar]] = {}
    for bar in bars:
        indexed.setdefault(bar.dt, []).append(bar)
    return indexed


def _unique_frequencies(frequencies: list[str]) -> list[str]:
    unique: list[str] = []
    for freq in frequencies:
        if freq not in unique:
            unique.append(freq)
    return unique


def _empty_history(fields) -> pd.DataFrame:
    if fields is not None:
        return pd.DataFrame(columns=["dt", *fields])
    return pd.DataFrame(
        columns=["symbol", "dt", "open", "high", "low", "close", "volume", "amount"]
    )


def _risk_reject_reason(rule_id: str | None, reason: str | None) -> str:
    if rule_id and reason:
        return f"{rule_id}: {reason}"
    return reason or rule_id or "risk rejected order"
