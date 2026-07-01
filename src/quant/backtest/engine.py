from dataclasses import dataclass, field, replace
from datetime import datetime, time
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from quant.backtest.clock import BacktestClock
from quant.backtest.events import EventJournal, JournalEvent
from quant.backtest.matcher import Matcher
from quant.core.config import RiskMoneyLimit, StrategyConfig
from quant.core.contract import (
    Bar,
    EngineState,
    Instrument,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    StrategyBase,
    Trade,
)
from quant.core.portfolio import Portfolio
from quant.costs import cost_model_from_config
from quant.data.service import DataService
from quant.risk.pipeline import RiskEngine, RiskLimits
from quant.risk.portfolio_stop import PortfolioStopEvent, portfolio_stop_config_from_mapping


@dataclass(frozen=True)
class BacktestResult:
    orders: list[Order]
    trades: list[Trade]
    equity: list[dict[str, object]]
    events: list[JournalEvent] = field(default_factory=list)
    cost_report_inputs: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TargetIntent:
    strategy_id: str
    symbol: str
    target_qty: float
    created_at: datetime
    correlation_id: str
    source_bar_timestamp: datetime | None = None
    target_value: float | None = None
    target_weight: float | None = None
    valuation_price: float | None = None


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
            raise ValueError(
                f"history frequency {freq!r} is not configured for BacktestClock; "
                "add it to frequencies.history"
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

    def set_target_value(self, symbol: str, target_value: float) -> None:
        self.engine.set_target_value(symbol=symbol, target_value=target_value)

    def set_target_weight(self, symbol: str, target_weight: float) -> None:
        self.engine.set_target_weight(symbol=symbol, target_weight=target_weight)

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
        self._validate_currency_coherence()
        self.journal = EventJournal(run_id=self.run_id)
        self.now = datetime(1970, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.portfolio = Portfolio(
            account_id="backtest",
            initial_cash=initial_cash,
            currency=config.account.currency,
            settlement=config.account.settlement,
            allow_fractional=config.account.allow_fractional,
        )
        self.matcher = Matcher(volume_limit_pct=0.05)
        self.risk = RiskEngine(self._build_risk_limits())
        if self.risk.portfolio_stop is not None:
            self.risk.portfolio_stop.set_event_sink(self._append_portfolio_stop_event)
        self.cost_model = cost_model_from_config(config.costs)
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
        self.total_fee = 0.0
        self.estimated_slippage_cost = 0.0
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
        if self.config.primary_frequency == "1d" and self.config.calendar != "continuous_24x7":
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
            cost_report_inputs=self._cost_report_inputs(),
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
            else:
                self.portfolio.mark_new_bar()
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
            else:
                self.portfolio.mark_new_bar()
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
        correlation_id = self._next_target_correlation_id()
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

    def set_target_value(self, *, symbol: str, target_value: float) -> None:
        correlation_id = self._next_target_correlation_id()
        if target_value < 0:
            self._reject_target_intent(
                symbol=symbol,
                correlation_id=correlation_id,
                risk_rule_id="target_value_range",
                reason="target value must be non-negative",
                payload={"target_value": target_value},
            )
            return
        self._set_sized_target(
            symbol=symbol,
            target_value=target_value,
            target_weight=None,
            correlation_id=correlation_id,
        )

    def set_target_weight(self, *, symbol: str, target_weight: float) -> None:
        correlation_id = self._next_target_correlation_id()
        if target_weight < 0.0 or target_weight > 1.0:
            self._reject_target_intent(
                symbol=symbol,
                correlation_id=correlation_id,
                risk_rule_id="target_weight_range",
                reason="target weight must be between 0.0 and 1.0",
                payload={"target_weight": target_weight},
            )
            return

        account = self.portfolio.account(self.last_prices)
        if account.total_value <= 0:
            self._reject_target_intent(
                symbol=symbol,
                correlation_id=correlation_id,
                risk_rule_id="gross_exposure",
                reason="account total value must be positive",
                payload={"target_weight": target_weight},
            )
            return

        self._set_sized_target(
            symbol=symbol,
            target_value=round(account.total_value * target_weight, 12),
            target_weight=target_weight,
            correlation_id=correlation_id,
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
        qty = self.portfolio.settlement_rules.round_qty(
            qty,
            self._instrument_for_settlement(symbol),
        )
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

    def cancel_order(self, order_id: str, *, reason: str = "strategy_cancel_requested") -> None:
        remaining: list[Order] = []
        cancelled_order: Order | None = None
        for order in self.open_orders:
            if order.order_id != order_id:
                remaining.append(order)
                continue
            cancelled_order = replace(
                order,
                status=OrderStatus.CANCELLED,
                updated_at=self.now,
            )
        if cancelled_order is None:
            return
        self.open_orders = remaining
        self.orders = [
            cancelled_order if order.order_id == order_id else order for order in self.orders
        ]
        correlation_id = self.order_correlation_ids.get(order_id)
        self._append_event(
            "order_cancelled",
            strategy_id=cancelled_order.strategy_id,
            account_id=cancelled_order.account_id,
            symbol=cancelled_order.symbol,
            order_id=order_id,
            correlation_id=correlation_id,
            payload={
                "side": cancelled_order.side.value,
                "type": cancelled_order.type.value,
                "qty": cancelled_order.qty,
                "price": cancelled_order.price,
                "filled_qty": cancelled_order.filled_qty,
                "remaining_qty": cancelled_order.remaining_qty,
                "status": OrderStatus.CANCELLED.value,
                "reason": reason,
            },
        )

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
        pending = self._reject_over_gross_target_weight_batches(pending)
        pending = self._reject_portfolio_stop_opening_targets(pending)
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
            executable_qty = self.portfolio.settlement_rules.round_qty(
                abs(diff),
                self._instrument_for_settlement(intent.symbol),
            )
            self._append_event(
                "rebalance_decision",
                symbol=intent.symbol,
                correlation_id=intent.correlation_id,
                payload={
                    "target_qty": intent.target_qty,
                    "current_qty": current,
                    "diff_qty": diff,
                    "price": price,
                    "action": "noop" if diff == 0 or executable_qty == 0 else "submit_order",
                },
            )
            if diff == 0 or executable_qty == 0:
                continue
            side = OrderSide.BUY if diff > 0 else OrderSide.SELL
            for qty in self._split_executable_order_qty(
                symbol=intent.symbol,
                qty=executable_qty,
                price=price,
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

    def _set_sized_target(
        self,
        *,
        symbol: str,
        target_value: float,
        target_weight: float | None,
        correlation_id: str,
    ) -> None:
        valuation_price = self._target_valuation_price(symbol)
        if valuation_price is None or valuation_price <= 0:
            self._reject_target_intent(
                symbol=symbol,
                correlation_id=correlation_id,
                risk_rule_id="valuation_price",
                reason="valuation price must be positive",
                payload={
                    "target_value": target_value,
                    "target_weight": target_weight,
                    "valuation_price": valuation_price,
                },
            )
            return

        instrument = self._instrument_for_settlement(symbol)
        target_qty = self.portfolio.settlement_rules.round_qty(
            target_value / valuation_price,
            instrument,
        )
        intent = TargetIntent(
            strategy_id=self.config.id,
            symbol=symbol,
            target_qty=target_qty,
            created_at=self.now,
            correlation_id=correlation_id,
            source_bar_timestamp=self._source_bar_timestamp(),
            target_value=target_value,
            target_weight=target_weight,
            valuation_price=valuation_price,
        )
        self.pending_targets.append(intent)
        self._append_event(
            "target_intent",
            symbol=symbol,
            correlation_id=correlation_id,
            payload=_target_intent_payload(intent),
        )

    def _reject_over_gross_target_weight_batches(
        self,
        pending: list[TargetIntent],
    ) -> list[TargetIntent]:
        batches: dict[datetime, list[TargetIntent]] = {}
        for intent in pending:
            if intent.target_weight is None:
                continue
            batches.setdefault(intent.created_at, []).append(intent)

        rejected_correlation_ids: set[str] = set()
        for batch in batches.values():
            batch_gross_weight = round(
                sum(abs(intent.target_weight or 0.0) for intent in batch),
                12,
            )
            if batch_gross_weight <= self.risk.limits.max_gross_exposure_pct:
                continue
            reason = "target weight batch exceeds max gross exposure"
            self._append_event(
                "risk_check",
                risk_rule_id="gross_exposure",
                payload={
                    "action": "reject_target_batch",
                    "allowed": False,
                    "batch_gross_weight": batch_gross_weight,
                    "max_gross_exposure_pct": self.risk.limits.max_gross_exposure_pct,
                    "reason": reason,
                    "target_count": len(batch),
                },
            )
            for intent in batch:
                rejected_correlation_ids.add(intent.correlation_id)
                self._append_event(
                    "target_intent_rejected",
                    symbol=intent.symbol,
                    risk_rule_id="gross_exposure",
                    correlation_id=intent.correlation_id,
                    payload={
                        **_target_intent_payload(intent),
                        "reason": reason,
                    },
                )

        return [
            intent
            for intent in pending
            if intent.correlation_id not in rejected_correlation_ids
        ]

    def _reject_portfolio_stop_opening_targets(
        self,
        pending: list[TargetIntent],
    ) -> list[TargetIntent]:
        stop = self.risk.portfolio_stop
        if stop is None or stop.allows_opening_exposure(self.now):
            return pending

        allowed: list[TargetIntent] = []
        reason = stop.opening_exposure_reject_reason(self.now)
        for intent in pending:
            current = self._effective_target_qty(intent.symbol)
            if intent.target_qty > current:
                self._reject_target_intent(
                    symbol=intent.symbol,
                    correlation_id=intent.correlation_id,
                    risk_rule_id="portfolio_stop_cooldown",
                    reason=reason,
                    payload=_target_intent_payload(intent),
                )
                continue
            allowed.append(intent)
        return allowed

    def _enqueue_defensive_targets(self, defensive_target: dict[str, Any] | None) -> None:
        if defensive_target is None or defensive_target.get("mode") != "flat":
            return
        for symbol, state in self.portfolio.positions.items():
            mark = self.last_prices.get(symbol, state.avg_price)
            current_qty = self.portfolio.position(symbol, mark_price=mark).qty
            if current_qty <= 0:
                continue
            correlation_id = self._next_target_correlation_id()
            intent = TargetIntent(
                strategy_id=self.config.id,
                symbol=symbol,
                target_qty=0.0,
                created_at=self.now,
                correlation_id=correlation_id,
                source_bar_timestamp=self._source_bar_timestamp(),
                target_value=0.0,
                target_weight=0.0,
                valuation_price=mark,
            )
            self.pending_targets.append(intent)
            self._append_event(
                "target_intent",
                source_component="quant.risk.portfolio_stop",
                symbol=symbol,
                risk_rule_id="portfolio_stop_drawdown",
                correlation_id=correlation_id,
                payload={
                    **_target_intent_payload(intent),
                    "reason": "portfolio_stop_defensive_target",
                    "defensive_target": dict(defensive_target),
                },
            )

    def _target_valuation_price(self, symbol: str) -> float | None:
        price = self.last_prices.get(symbol)
        if price is not None:
            return price
        bar = self.current_bars.get(symbol)
        return bar.close if bar is not None else None

    def _source_bar_timestamp(self) -> datetime:
        return self.get_visible_bar_time(self.config.primary_frequency) or self.now

    def _next_target_correlation_id(self) -> str:
        self._target_seq += 1
        return f"target-{self._target_seq}"

    def _reject_target_intent(
        self,
        *,
        symbol: str,
        correlation_id: str,
        risk_rule_id: str,
        reason: str,
        payload: dict[str, Any],
    ) -> None:
        self._append_event(
            "risk_check",
            symbol=symbol,
            risk_rule_id=risk_rule_id,
            correlation_id=correlation_id,
            payload={
                "action": "reject_target_intent",
                "allowed": False,
                "reason": reason,
                **payload,
            },
        )
        self._append_event(
            "target_intent_rejected",
            symbol=symbol,
            risk_rule_id=risk_rule_id,
            correlation_id=correlation_id,
            payload={"reason": reason, **payload},
        )

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

    def _instrument_for_settlement(self, symbol: str) -> Instrument:
        instrument = self.data.get_instrument(symbol)
        allow_fractional = self._instrument_allows_fractional(symbol, instrument.allow_fractional)
        manifest = getattr(self.data, "_manifest", None)
        if manifest is None:
            return replace(instrument, allow_fractional=allow_fractional)
        symbol_manifest = None
        for candidate in manifest.symbols:
            if candidate.symbol == symbol:
                symbol_manifest = candidate
                break
        if symbol_manifest is None:
            return replace(instrument, allow_fractional=allow_fractional)
        manifest_allow_fractional = getattr(symbol_manifest, "allow_fractional", None)
        if manifest_allow_fractional is not None:
            allow_fractional = _coerce_bool(manifest_allow_fractional, default=allow_fractional)
        return replace(
            instrument,
            lot_size=symbol_manifest.lot_size,
            qty_step=symbol_manifest.qty_step,
            t_plus=symbol_manifest.t_plus,
            allow_fractional=allow_fractional,
            quote_currency=manifest.quote_currency,
        )

    def _instrument_allows_fractional(self, symbol: str, default: bool) -> bool:
        instruments = getattr(self.data, "_instruments", None)
        if instruments is None or "allow_fractional" not in instruments.columns:
            return default
        row = instruments[instruments["symbol"] == symbol]
        if row.empty:
            return default
        return _coerce_bool(row.iloc[0]["allow_fractional"], default=default)

    def _split_executable_order_qty(self, *, symbol: str, qty: float, price: float) -> list[float]:
        if qty <= 0:
            return []
        max_order_value = self.risk.limits.max_order_value
        if (
            price <= 0
            or max_order_value is None
            or max_order_value <= 0
            or qty * price <= max_order_value
        ):
            return [qty]

        instrument = self._instrument_for_settlement(symbol)
        raw_limit = (max_order_value / price) * (1 - 1e-12)
        chunks: list[float] = []
        remaining = qty
        while remaining > 0:
            if remaining * price <= max_order_value:
                chunks.append(remaining)
                break
            chunk = self.portfolio.settlement_rules.round_qty(
                min(remaining, raw_limit),
                instrument,
            )
            if chunk <= 0:
                chunks.append(remaining)
                break
            chunks.append(chunk)
            remaining = round(remaining - chunk, 12)
        return chunks

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
            cost_breakdown = self.cost_model.calculate_breakdown(
                order.side,
                result.filled_qty,
                result.fill_price,
            )
            commission = cost_breakdown.fee
            self.total_fee = round(self.total_fee + cost_breakdown.fee, 2)
            self.estimated_slippage_cost = round(
                self.estimated_slippage_cost + cost_breakdown.estimated_slippage_cost,
                2,
            )
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
            self.portfolio.apply_trade(
                trade,
                instrument=self._instrument_for_settlement(order.symbol),
            )
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
            fill_payload = {
                "side": order.side.value,
                "qty": result.filled_qty,
                "price": result.fill_price,
                "commission": commission,
                "order_status": status.value,
                "remaining_qty": remaining_qty,
                **cost_breakdown.fill_event_fields(),
            }
            self._append_event(
                "fill",
                timestamp=bar.dt,
                symbol=order.symbol,
                order_id=order.order_id,
                trade_id=trade.trade_id,
                correlation_id=correlation_id,
                payload=fill_payload,
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
        if self.risk.portfolio_stop is None:
            return
        decision = self.risk.portfolio_stop.on_equity(self.now, account.total_value)
        if decision.triggered:
            self._enqueue_defensive_targets(decision.defensive_target)

    def _cost_report_inputs(self) -> dict[str, object]:
        return {
            **self.cost_model.report_inputs(),
            "total_fee": round(self.total_fee, 2),
            "estimated_slippage_cost": round(self.estimated_slippage_cost, 2),
        }

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

    def _append_portfolio_stop_event(self, event: PortfolioStopEvent) -> None:
        self._append_event(
            event.event_type,
            timestamp=event.timestamp,
            source_component="quant.risk.portfolio_stop",
            risk_rule_id=event.risk_rule_id,
            payload=event.payload,
        )

    def _build_risk_limits(self) -> RiskLimits:
        risk = self.config.risk
        account_value = self.portfolio.account({}).total_value
        quote_currency = self._quote_currency()
        return RiskLimits(
            universe=set(self.config.universe),
            calendar=self.config.calendar,
            max_order_value=_resolve_money_limit(
                risk.max_order_value,
                account_currency=self.config.account.currency,
                quote_currency=quote_currency,
                account_value=account_value,
                default=200_000,
            ),
            max_position_value_per_symbol=(
                _resolve_money_limit(
                    risk.max_position_value,
                    account_currency=self.config.account.currency,
                    quote_currency=quote_currency,
                    account_value=account_value,
                    default=500_000,
                )
            ),
            max_gross_exposure_pct=(
                risk.max_gross_exposure_pct if risk.max_gross_exposure_pct is not None else 0.95
            ),
            max_orders_per_minute=(
                risk.max_orders_per_minute if risk.max_orders_per_minute is not None else 10
            ),
            portfolio_stop=portfolio_stop_config_from_mapping(
                getattr(risk, "portfolio_stop", None)
            ),
        )

    def _quote_currency(self) -> str:
        manifest = getattr(self.data, "_manifest", None)
        if manifest is None:
            return self.config.account.currency
        return manifest.quote_currency

    def _validate_currency_coherence(self) -> None:
        manifest = getattr(self.data, "_manifest", None)
        if manifest is None:
            return
        if not _same_currency(manifest.quote_currency, self.config.account.currency):
            raise ValueError(
                f"dataset quote_currency {manifest.quote_currency} does not match "
                f"account currency {self.config.account.currency}"
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


def _target_intent_payload(intent: TargetIntent) -> dict[str, object]:
    return {
        "source_bar_timestamp": (
            intent.source_bar_timestamp.isoformat()
            if intent.source_bar_timestamp is not None
            else None
        ),
        "target_qty": intent.target_qty,
        "target_value": intent.target_value,
        "target_weight": intent.target_weight,
        "valuation_price": intent.valuation_price,
    }


def _risk_reject_reason(rule_id: str | None, reason: str | None) -> str:
    if rule_id and reason:
        return f"{rule_id}: {reason}"
    return reason or rule_id or "risk rejected order"


def _resolve_money_limit(
    limit: RiskMoneyLimit | float | None,
    *,
    account_currency: str,
    quote_currency: str,
    account_value: float,
    default: float,
) -> float:
    if limit is None:
        return default
    if isinstance(limit, RiskMoneyLimit):
        if limit.unit == "equity_pct":
            return float(account_value * limit.value)
        if limit.unit == "currency":
            if not _same_currency(limit.currency, account_currency):
                raise ValueError(
                    f"risk money limit currency {limit.currency} does not match account "
                    f"currency {account_currency}"
                )
        if limit.unit == "quote_currency" and limit.currency is not None:
            if not _same_currency(limit.currency, quote_currency):
                raise ValueError(
                    f"risk money limit quote currency {limit.currency} does not match "
                    f"account currency {account_currency}"
                )
        return float(limit.value)
    return float(limit)


def _same_currency(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left == right
    return left.strip().upper() == right.strip().upper()


def _coerce_bool(value: object, *, default: bool) -> bool:
    if value is None or pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized == "":
        return default
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"allow_fractional must be boolean, got {value!r}")
