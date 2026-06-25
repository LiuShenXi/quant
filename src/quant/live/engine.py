from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

from quant.core.config import StrategyConfig
from quant.core.contract import Account, Bar, Order, StrategyBase, Trade
from quant.data.service import DataService
from quant.live.alerts import AlertManager
from quant.live.config import GlobalRiskConfig, PaperConfig
from quant.live.context import PaperContext, _PaperContextRuntime
from quant.live.events import EventJournal
from quant.live.execution import ExecutionRouter
from quant.live.gateway.base import GatewayBase
from quant.live.gateway.factory import build_sim_gateway
from quant.live.monitor import RuntimeMonitor
from quant.live.oms import OrderManager
from quant.live.reconcile import Reconciler, ReconciliationResult, ReconciliationStatus
from quant.live.store import OmsStore
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot
from quant.risk.pipeline import RiskEngine, RiskLimits


@dataclass(frozen=True)
class PaperRunResult:
    orders: list[Order]
    trades: list[Trade]
    final_state: str
    events_path: str
    store_path: str
    startup_reconciliation: ReconciliationResult
    close_reconciliation: ReconciliationResult
    drill_events: list[dict[str, object]] = field(default_factory=list)


class PaperEngine:
    def __init__(
        self,
        strategy_config: StrategyConfig,
        paper_config: PaperConfig,
        global_risk_config: GlobalRiskConfig | None = None,
        gateway_factory: Callable[[PaperConfig, OmsStore], GatewayBase] | None = None,
    ) -> None:
        if strategy_config.runtime_mode != "paper":
            raise ValueError("runtime_mode must be paper")

        self.strategy_config = strategy_config
        self.paper_config = paper_config
        self.global_risk_config = global_risk_config
        self.data = DataService(paper_config.data_root)
        self.now = datetime(1970, 1, 1, tzinfo=ZoneInfo(paper_config.timezone))
        self.current_bar: Bar | None = None
        self.latest_prices: dict[str, float] = {}
        self.state: dict[str, Any] = {"timers": {}, "logs": []}

        self.store = OmsStore(paper_config.store_path)
        self.store.init_schema()
        self.paper_config.run_root.mkdir(parents=True, exist_ok=True)

        self.journal = EventJournal(
            paper_config.events_path,
            timezone=paper_config.timezone,
            clock=lambda: self.now,
        )
        self.gateway = self._build_gateway(gateway_factory)
        self.risk = RiskEngine(self._build_risk_limits())
        self.oms = OrderManager(
            account_id=paper_config.account_id,
            gateway=self.gateway,
            store=self.store,
            journal=self.journal,
            risk=self.risk,
            clock=lambda: self.now,
        )
        self.reconciler = Reconciler(
            store=self.store,
            gateway=self.gateway,
            journal=self.journal,
            cash_tolerance=paper_config.reconciliation.cash_tolerance,
            position_qty_tolerance=paper_config.reconciliation.position_qty_tolerance,
            auto_repair_cash_drift_below=paper_config.reconciliation.auto_repair_cash_drift_below,
            clock=lambda: self.now,
        )
        self.alert_manager = AlertManager(
            self.journal,
            dedupe_sec=paper_config.monitor.alert_dedupe_sec,
            clock=lambda: self.now,
            delivery_dir=paper_config.run_root / "alert_delivery",
        )
        self.monitor = RuntimeMonitor(
            store=self.store,
            journal=self.journal,
            alert_manager=self.alert_manager,
            market_data_staleness_sec=paper_config.monitor.market_data_staleness_sec,
            run_id=self._run_id(),
            strategy_id=strategy_config.id,
            account_id=paper_config.account_id,
            clock=lambda: self.now,
        )
        self.execution_router = ExecutionRouter(self.oms, self.gateway.query_positions)
        self.context = PaperContext(
            runtime=self._context_runtime(),
            strategy_id=strategy_config.id,
        )
        self.strategy: StrategyBase | None = None

        self.gateway.set_callbacks(
            on_bar=self._on_bar,
            on_order=self._on_broker_order,
            on_trade=self._on_broker_trade,
            on_disconnect=self._on_disconnect,
        )

    def run_replay(
        self,
        max_bars: int | None = None,
        *,
        disconnect_drill: bool = False,
        disconnect_reason: str = "disconnect drill",
    ) -> PaperRunResult:
        bars = self.data.load_bars(self.strategy_config.universe)
        if max_bars is not None:
            bars = bars[:max_bars]
        if not bars:
            raise ValueError("no replay bars available")

        self.now = bars[0].dt
        self._bootstrap_account_if_needed()
        startup_reconciliation = self.reconciler.run(startup=True)
        if startup_reconciliation.status == ReconciliationStatus.FAILED:
            raise RuntimeError(f"startup reconciliation failed: {startup_reconciliation.message}")

        strategy = self._load_strategy()
        self.strategy = strategy
        strategy.on_init(self.context)
        strategy.on_start(self.context)

        previous_date: date | None = None
        for bar_date, day_bars in _group_bars_by_date(bars):
            if previous_date is not None and bar_date != previous_date:
                self.gateway.mark_new_day()
                self._save_gateway_snapshot()
            previous_date = bar_date
            send_time = datetime.combine(
                bar_date,
                time(9, 31),
                tzinfo=ZoneInfo(self.paper_config.timezone),
            )
            self.now = send_time
            latest_prices = {bar.symbol: bar.open for bar in day_bars}
            market_data_stale = self._check_market_data_before_target_flush(
                now=self.now,
                day_bars=day_bars,
                latest_prices=latest_prices,
            )
            if market_data_stale:
                continue
            self.execution_router.flush_pending(now=self.now, latest_prices=latest_prices)

            for bar in day_bars:
                self.current_bar = bar
                self.latest_prices[bar.symbol] = bar.close
                self.now = bar.dt
                self.gateway.push_bar(bar)
                self._refresh_snapshot_and_apply_equity_kill_switch()
                strategy.on_bar(self.context, bar)

        strategy.on_stop(self.context)
        close_reconciliation = self.reconciler.run(startup=False)
        drill_events = []
        if disconnect_drill:
            drill_events.append(self.run_disconnect_drill(disconnect_reason))
        return PaperRunResult(
            orders=self.store.list_orders(),
            trades=self.store.list_trades(),
            final_state=self.store.get_engine_state().value,
            events_path=str(self.paper_config.events_path),
            store_path=str(self.paper_config.store_path),
            startup_reconciliation=startup_reconciliation,
            close_reconciliation=close_reconciliation,
            drill_events=drill_events,
        )

    def latest_price(self, symbol: str) -> float:
        if self.current_bar is not None and self.current_bar.symbol == symbol:
            return self.current_bar.close
        return self.latest_prices.get(symbol, 0.0)

    def _build_risk_limits(self) -> RiskLimits:
        risk = self.strategy_config.risk
        global_risk = self.global_risk_config
        return RiskLimits(
            universe=set(self.strategy_config.universe),
            price_collar_pct=global_risk.price_collar_pct if global_risk is not None else 0.02,
            max_order_value=_tighten_limit(
                global_risk.max_order_value if global_risk is not None else 200_000,
                risk.max_order_value,
            ),
            max_position_value_per_symbol=(
                _tighten_limit(
                    (
                        global_risk.max_position_value_per_symbol
                        if global_risk is not None
                        else 500_000
                    ),
                    risk.max_position_value,
                )
            ),
            max_gross_exposure_pct=(
                _tighten_limit(
                    global_risk.max_gross_exposure_pct if global_risk is not None else 0.95,
                    risk.max_gross_exposure_pct,
                )
            ),
            max_orders_per_minute=(
                int(
                    _tighten_limit(
                        global_risk.max_orders_per_minute if global_risk is not None else 10,
                        risk.max_orders_per_minute,
                    )
                )
            ),
            daily_loss_freeze_pct=(
                global_risk.kill_switch.daily_loss_freeze_pct
                if global_risk is not None
                else 0.02
            ),
            daily_loss_halt_pct=(
                global_risk.kill_switch.daily_loss_halt_pct if global_risk is not None else 0.04
            ),
        )

    def _build_gateway(
        self,
        gateway_factory: Callable[[PaperConfig, OmsStore], GatewayBase] | None,
    ) -> GatewayBase:
        if gateway_factory is not None:
            return gateway_factory(self.paper_config, self.store)
        return build_sim_gateway(self.paper_config, self.store)

    def _load_strategy(self) -> StrategyBase:
        module_name, class_name = self.strategy_config.class_path.split(":")
        module = import_module(module_name)
        strategy_class = getattr(module, class_name)
        return strategy_class()

    def _bootstrap_account_if_needed(self) -> None:
        if self.store.load_account_snapshot() is not None or not self.store.is_empty():
            return

        account = Account(
            account_id=self.paper_config.account_id,
            currency="CNY",
            cash=self.paper_config.initial_cash,
            frozen=0,
            market_value=0,
            total_value=self.paper_config.initial_cash,
        )
        self.store.save_account_snapshot(account, {}, self.now)
        self.journal.append(
            "account_bootstrap",
            {
                "account_id": account.account_id,
                "cash": account.cash,
                "positions": {},
            },
        )

    def _on_bar(self, bar: Bar) -> None:
        self.current_bar = bar
        self.latest_prices[bar.symbol] = bar.close

    def _on_broker_order(self, snapshot: BrokerOrderSnapshot) -> None:
        order = self.oms.on_broker_order(snapshot)
        if self.strategy is not None:
            self.strategy.on_order(self.context, order)

    def _on_broker_trade(self, snapshot: BrokerTradeSnapshot) -> None:
        trade = self.oms.on_broker_trade(snapshot)
        if trade is not None and self.strategy is not None:
            self.strategy.on_trade(self.context, trade)

    def _on_disconnect(self, reason: str) -> None:
        self.monitor.on_gateway_disconnect(reason)

    def run_disconnect_drill(self, reason: str) -> dict[str, object]:
        self.gateway.inject_disconnect(reason)
        self.gateway.reconnect()
        reconciliation = self.reconciler.run(startup=False)
        recovered_state = self.monitor.on_gateway_reconnect(
            reconciliation_ok=reconciliation.status in {
                ReconciliationStatus.OK,
                ReconciliationStatus.REPAIRED,
            }
        )
        result = {
            "reason": reason,
            "reconciliation_status": reconciliation.status.value,
            "final_state": recovered_state.value,
        }
        self.journal.append("disconnect_drill", result)
        return result

    def _save_gateway_snapshot(self) -> Account:
        account = self.gateway.query_account()
        positions = self.gateway.query_positions()
        self.store.save_account_snapshot(account, positions, self.now)
        return account

    def _refresh_snapshot_and_apply_equity_kill_switch(self) -> None:
        account = self._save_gateway_snapshot()
        state = self.risk.on_equity(account.total_value, self.now)
        if state is None:
            return
        reason = "daily_loss_halt" if state.value == "HALT" else "daily_loss_freeze"
        if state.value == "HALT":
            self.oms.halt(reason)
        else:
            self.oms.freeze_open(reason)

    def _run_id(self) -> str:
        return f"paper-{self.strategy_config.id}-{self.paper_config.account_id}"

    def _context_runtime(self) -> _PaperContextRuntime:
        return _PaperContextRuntime(
            account_id=self.paper_config.account_id,
            now=lambda: self.now,
            params=lambda: self.strategy_config.params,
            history=self.data.history,
            query_positions=self.gateway.query_positions,
            query_account=self.gateway.query_account,
            list_open_orders=lambda: self.store.list_orders(active_only=True),
            latest_price=self.latest_price,
            submit_order=self.oms.submit_order,
            set_target=self.execution_router.set_target,
            cancel_order=self.oms.cancel_order,
            current_bar=lambda: self.current_bar,
            get_instrument=self.data.get_instrument,
            schedule=self._schedule_timer,
            log=self._append_strategy_log,
            save_kv=self.store.save_kv,
            load_kv=self.store.load_kv,
        )

    def _schedule_timer(self, timer_id: str, at: str) -> None:
        self.state["timers"][timer_id] = at

    def _append_strategy_log(self, msg: str, level: str) -> None:
        self.state["logs"].append(
            {"level": level, "message": msg, "at": self.now.isoformat()}
        )

    def _check_market_data_before_target_flush(
        self,
        *,
        now: datetime,
        day_bars: list[Bar],
        latest_prices: dict[str, float],
    ) -> bool:
        pending_symbols = {
            intent.symbol for intent in self.execution_router.pending_targets
        }
        if not pending_symbols:
            return False

        if not pending_symbols.issubset(latest_prices):
            self.monitor.check_market_data(now=now, last_bar_at=None)
            return True

        daily_data_at = datetime.combine(
            day_bars[0].dt.date(),
            time(9, 31),
            tzinfo=ZoneInfo(self.paper_config.timezone),
        )
        return self.monitor.check_market_data(
            now=now,
            last_bar_at=daily_data_at,
        ) is not None


def _group_bars_by_date(bars: list[Bar]) -> list[tuple[date, list[Bar]]]:
    groups: list[tuple[date, list[Bar]]] = []
    current_date: date | None = None
    current_group: list[Bar] = []
    for bar in bars:
        bar_date = bar.dt.date()
        if current_date is None or bar_date != current_date:
            if current_group:
                groups.append((current_date, current_group))
            current_date = bar_date
            current_group = [bar]
        else:
            current_group.append(bar)
    if current_group:
        groups.append((current_date, current_group))
    return groups


def _tighten_limit(global_value: float | int | None, strategy_value: float | int | None) -> float:
    values = [value for value in (global_value, strategy_value) if value is not None]
    if not values:
        raise ValueError("at least one risk limit value is required")
    return float(min(values))
