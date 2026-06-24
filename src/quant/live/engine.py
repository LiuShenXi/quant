from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

from quant.core.config import StrategyConfig
from quant.core.contract import Account, Bar, Order, StrategyBase, Trade
from quant.data.service import DataService
from quant.live.config import PaperConfig
from quant.live.context import PaperContext
from quant.live.events import EventJournal
from quant.live.execution import ExecutionRouter
from quant.live.gateway.sim import SimGateway
from quant.live.oms import OrderManager
from quant.live.reconcile import Reconciler
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


class PaperEngine:
    def __init__(self, strategy_config: StrategyConfig, paper_config: PaperConfig) -> None:
        if strategy_config.runtime_mode != "paper":
            raise ValueError("runtime_mode must be paper")

        self.strategy_config = strategy_config
        self.paper_config = paper_config
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
        self.gateway = SimGateway(
            initial_cash=paper_config.initial_cash,
            account_id=paper_config.account_id,
        )
        self.risk = RiskEngine(self._build_risk_limits())
        self.oms = OrderManager(
            account_id=paper_config.account_id,
            gateway=self.gateway,
            store=self.store,
            journal=self.journal,
            risk=self.risk,
        )
        self.reconciler = Reconciler(
            store=self.store,
            gateway=self.gateway,
            journal=self.journal,
            cash_tolerance=paper_config.reconciliation.cash_tolerance,
            position_qty_tolerance=paper_config.reconciliation.position_qty_tolerance,
            auto_repair_cash_drift_below=paper_config.reconciliation.auto_repair_cash_drift_below,
        )
        self.execution_router = ExecutionRouter(self.oms, self.gateway.query_positions)
        self.context = PaperContext(self, strategy_config.id)
        self.strategy: StrategyBase | None = None

        self.gateway.set_callbacks(
            on_bar=self._on_bar,
            on_order=self._on_broker_order,
            on_trade=self._on_broker_trade,
            on_disconnect=self._on_disconnect,
        )

    def run_replay(self, max_bars: int | None = None) -> PaperRunResult:
        bars = self.data.load_bars(self.strategy_config.universe)
        if max_bars is not None:
            bars = bars[:max_bars]
        if not bars:
            raise ValueError("no replay bars available")

        self.now = bars[0].dt
        strategy = self._load_strategy()
        self.strategy = strategy
        strategy.on_init(self.context)
        self._bootstrap_account_if_needed()
        self.reconciler.run(startup=True)
        strategy.on_start(self.context)

        for bar_date, day_bars in _group_bars_by_date(bars):
            send_time = datetime.combine(
                bar_date,
                time(9, 31),
                tzinfo=ZoneInfo(self.paper_config.timezone),
            )
            self.now = send_time
            latest_prices = {bar.symbol: bar.open for bar in day_bars}
            self.execution_router.flush_pending(now=self.now, latest_prices=latest_prices)

            for bar in day_bars:
                self.current_bar = bar
                self.latest_prices[bar.symbol] = bar.close
                self.now = bar.dt
                self.gateway.push_bar(bar)
                strategy.on_bar(self.context, bar)

        strategy.on_stop(self.context)
        return PaperRunResult(
            orders=self.store.list_orders(),
            trades=self.store.list_trades(),
            final_state=self.store.get_engine_state().value,
            events_path=str(self.paper_config.events_path),
            store_path=str(self.paper_config.store_path),
        )

    def latest_price(self, symbol: str) -> float:
        if self.current_bar is not None and self.current_bar.symbol == symbol:
            return self.current_bar.close
        return self.latest_prices.get(symbol, 0.0)

    def _build_risk_limits(self) -> RiskLimits:
        risk = self.strategy_config.risk
        return RiskLimits(
            universe=set(self.strategy_config.universe),
            price_collar_pct=0.02,
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
        self.oms.freeze_open(reason)


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
