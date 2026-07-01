from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

from quant.backtest.engine import BacktestEngine
from quant.core.config import RiskConfig, load_strategy_config
from quant.core.contract import Account, OrderSide, OrderStatus, OrderType, Position, StrategyBase
from quant.data.service import DataService
from quant.risk.pipeline import RiskEngine, RiskLimits
from quant.risk.portfolio_stop import (
    PortfolioStop,
    PortfolioStopConfig,
    PortfolioStopEvent,
    ReentryPredicateInput,
    ReentryPredicateValue,
)


TZ = ZoneInfo("Asia/Shanghai")


def test_trailing_peak_breach_enters_cooldown_and_emits_risk_events() -> None:
    events: list[PortfolioStopEvent] = []
    stop = PortfolioStop(
        PortfolioStopConfig(
            trailing_drawdown_pct=0.10,
            cooldown=timedelta(hours=2),
            defensive_target={"mode": "flat"},
        ),
        event_sink=events.append,
    )

    assert stop.on_equity(ts("2024-01-02T15:00:00+08:00"), 100_000).triggered is False
    assert stop.state.cycle_peak_value == 100_000

    stop.on_equity(ts("2024-01-03T15:00:00+08:00"), 120_000)
    decision = stop.on_equity(ts("2024-01-04T15:00:00+08:00"), 107_900)

    assert decision.triggered is True
    assert decision.defensive_target == {"mode": "flat"}
    assert stop.state.cycle_state == "COOLDOWN"
    assert stop.state.cycle_peak_value == 120_000
    assert stop.state.stop_triggered_at == ts("2024-01-04T15:00:00+08:00")
    assert stop.state.cooldown_until == ts("2024-01-04T17:00:00+08:00")
    assert [event.event_type for event in events] == [
        "risk_portfolio_stop",
        "risk_cooldown_start",
    ]
    assert events[0].payload["drawdown_pct"] > 0.10
    assert events[0].payload["defensive_target"] == {"mode": "flat"}


def test_cooldown_blocks_new_opening_exposure_but_allows_reducing_sell() -> None:
    engine = RiskEngine(
        RiskLimits(
            universe={"AAA.SH"},
            max_order_value=500_000,
            max_position_value_per_symbol=500_000,
            max_gross_exposure_pct=2,
            portfolio_stop=PortfolioStopConfig(
                trailing_drawdown_pct=0.05,
                cooldown=timedelta(hours=4),
                defensive_target={"mode": "flat"},
            ),
        )
    )
    engine.portfolio_stop.on_equity(ts("2024-01-02T15:00:00+08:00"), 100_000)
    engine.portfolio_stop.on_equity(ts("2024-01-03T15:00:00+08:00"), 94_000)
    position = Position("AAA.SH", "backtest", qty=100, sellable=100, avg_price=100, market_value=9_400)

    buy = engine.check_order(
        make_req(OrderSide.BUY),
        latest_price=94,
        account=make_account(total_value=94_000),
        positions={"AAA.SH": position},
        active_orders=[],
        now=ts("2024-01-04T09:31:00+08:00"),
        state="NORMAL",
    )
    sell = engine.check_order(
        make_req(OrderSide.SELL),
        latest_price=94,
        account=make_account(total_value=94_000),
        positions={"AAA.SH": position},
        active_orders=[],
        now=ts("2024-01-04T09:31:00+08:00"),
        state="NORMAL",
    )

    assert buy.allowed is False
    assert buy.rule_id == "portfolio_stop_cooldown"
    assert sell.allowed is True


def test_reentry_predicate_false_keeps_defensive_target_and_records_audit_event() -> None:
    events: list[PortfolioStopEvent] = []
    stop = stopped_portfolio_stop(events)

    result = stop.check_reentry(
        ReentryPredicateInput(
            predicate_id="toy_reentry",
            as_of=ts("2024-01-03T16:00:00+08:00"),
            decision_time=ts("2024-01-03T16:00:00+08:00"),
            required_cooling_until=stop.state.cooldown_until,
            result=False,
            inputs=[
                ReentryPredicateValue(
                    name="toy_signal",
                    source_component="tests",
                    freq="1d",
                    visible_bar_dt=ts("2024-01-03T15:00:00+08:00"),
                    construction="closed_bar_fixture",
                    value={"ok": False},
                    fully_closed=True,
                )
            ],
        )
    )

    assert result is False
    assert stop.state.cycle_state == "STOPPED"
    assert stop.state.defensive_target == {"mode": "flat"}
    check = events[-1]
    assert check.event_type == "risk_reentry_check"
    assert check.payload["predicate_id"] == "toy_reentry"
    assert check.payload["result"] is False
    assert check.payload["reason"] == "predicate_false"
    assert check.payload["inputs"][0]["visible_bar_dt"] == "2024-01-03T15:00:00+08:00"


def test_reentry_predicate_true_resets_state_emits_audit_and_allows_opening_exposure() -> None:
    events: list[PortfolioStopEvent] = []
    engine = RiskEngine(
        RiskLimits(
            universe={"AAA.SH"},
            max_order_value=500_000,
            max_position_value_per_symbol=500_000,
            max_gross_exposure_pct=2,
            portfolio_stop=PortfolioStopConfig(
                trailing_drawdown_pct=0.05,
                cooldown=timedelta(hours=1),
                defensive_target={"mode": "flat"},
            ),
        )
    )
    assert engine.portfolio_stop is not None
    engine.portfolio_stop.set_event_sink(events.append)

    engine.portfolio_stop.on_equity(ts("2024-01-02T09:31:00+08:00"), 100_000)
    engine.portfolio_stop.on_equity(ts("2024-01-02T10:31:00+08:00"), 94_000)
    assert engine.portfolio_stop.state.cycle_state == "COOLDOWN"
    assert engine.portfolio_stop.state.cooldown_until == ts("2024-01-02T11:31:00+08:00")
    assert engine.portfolio_stop.state.defensive_target == {"mode": "flat"}

    blocked = engine.check_order(
        make_req(OrderSide.BUY, created_at=ts("2024-01-02T10:45:00+08:00")),
        latest_price=94,
        account=make_account(total_value=94_000),
        positions={},
        active_orders=[],
        now=ts("2024-01-02T10:45:00+08:00"),
        state="NORMAL",
    )
    assert blocked.allowed is False
    assert blocked.rule_id == "portfolio_stop_cooldown"

    result = engine.portfolio_stop.check_reentry(
        ReentryPredicateInput(
            predicate_id="toy_reentry",
            as_of=ts("2024-01-02T13:01:00+08:00"),
            decision_time=ts("2024-01-02T13:01:00+08:00"),
            required_cooling_until=ts("2024-01-02T11:31:00+08:00"),
            result=True,
            inputs=[
                ReentryPredicateValue(
                    name="toy_signal",
                    source_component="tests",
                    freq="1d",
                    visible_bar_dt=ts("2024-01-02T10:31:00+08:00"),
                    construction="closed_bar_fixture",
                    value={"ok": True},
                    fully_closed=True,
                )
            ],
        )
    )

    assert result is True
    assert engine.portfolio_stop.state.cycle_state == "ACTIVE"
    assert engine.portfolio_stop.state.cycle_peak_value is None
    assert engine.portfolio_stop.state.stop_triggered_at is None
    assert engine.portfolio_stop.state.cooldown_until is None
    assert engine.portfolio_stop.state.defensive_target is None
    assert engine.portfolio_stop.state.last_reentry_check is not None
    assert engine.portfolio_stop.state.last_reentry_check["result"] is True
    assert engine.portfolio_stop.state.last_reentry_check["reason"] == "predicate_true"

    reentry_events = [
        event
        for event in events
        if event.event_type in {"risk_reentry_check", "risk_portfolio_reentry"}
    ]
    assert [event.event_type for event in reentry_events] == [
        "risk_reentry_check",
        "risk_portfolio_reentry",
    ]
    assert reentry_events[0].payload["predicate_id"] == "toy_reentry"
    assert reentry_events[0].payload["result"] is True
    assert reentry_events[0].payload["reason"] == "predicate_true"
    assert reentry_events[1].payload["predicate_id"] == "toy_reentry"
    assert reentry_events[1].payload["result"] is True

    allowed = engine.check_order(
        make_req(OrderSide.BUY, created_at=ts("2024-01-02T13:01:00+08:00")),
        latest_price=94,
        account=make_account(total_value=94_000),
        positions={},
        active_orders=[],
        now=ts("2024-01-02T13:01:00+08:00"),
        state="NORMAL",
    )
    assert allowed.allowed is True


def test_missing_or_future_reentry_inputs_default_false_and_record_events() -> None:
    events: list[PortfolioStopEvent] = []
    stop = stopped_portfolio_stop(events)

    assert stop.check_reentry(None) is False
    assert stop.check_reentry(
        ReentryPredicateInput(
            predicate_id="toy_future",
            as_of=ts("2024-01-03T16:01:00+08:00"),
            decision_time=ts("2024-01-03T16:00:00+08:00"),
            required_cooling_until=stop.state.cooldown_until,
            result=True,
            inputs=[
                ReentryPredicateValue(
                    name="future_signal",
                    source_component="tests",
                    freq="1d",
                    visible_bar_dt=ts("2024-01-03T16:01:00+08:00"),
                    construction="future_bar_fixture",
                    value=True,
                    fully_closed=True,
                )
            ],
        )
    ) is False

    check_events = [event for event in events if event.event_type == "risk_reentry_check"]
    assert check_events[-2].payload["reason"] == "missing_input"
    assert check_events[-1].payload["predicate_id"] == "toy_future"
    assert check_events[-1].payload["reason"] == "future_as_of"
    assert check_events[-1].payload["result"] is False


def test_backtest_records_portfolio_stop_and_blocks_new_targets(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.portfolio_stop_repeat_target_strategy")

    class RepeatTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol:
                ctx.set_target(self.symbol, self.target_qty)

    strategy_module.RepeatTargetStrategy = RepeatTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module
            if name == "tests.portfolio_stop_repeat_target_strategy"
            else None
        ),
    )
    risk = RiskConfig(
        max_order_value=300_000,
        max_position_value=300_000,
        max_gross_exposure_pct=1,
    ).model_copy(
        update={
            "portfolio_stop": {
                "enabled": True,
                "trailing_drawdown_pct": 0.01,
                "cooldown_hours": 48,
                "defensive_target": {"mode": "flat"},
            }
        }
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.portfolio_stop_repeat_target_strategy:RepeatTargetStrategy",
            "universe": ["AAA.SH"],
            "params": {"symbol": "AAA.SH", "target_qty": 1_000},
            "risk": risk,
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(write_portfolio_stop_data(tmp_path)),
        initial_cash=200_000,
    ).run()

    event_types = [event.event_type for event in result.events]
    assert "risk_portfolio_stop" in event_types
    assert "risk_cooldown_start" in event_types
    assert any(
        event.event_type == "target_intent_rejected"
        and event.risk_rule_id == "portfolio_stop_cooldown"
        for event in result.events
    )
    assert any(order.side == OrderSide.SELL for order in result.orders)
    assert all(
        order.status == OrderStatus.REJECTED
        for order in result.orders
        if order.side == OrderSide.BUY and order.created_at >= ts("2024-01-04T09:31:00+08:00")
    )


def stopped_portfolio_stop(events: list[PortfolioStopEvent]) -> PortfolioStop:
    stop = PortfolioStop(
        PortfolioStopConfig(
            trailing_drawdown_pct=0.05,
            cooldown=timedelta(hours=1),
            defensive_target={"mode": "flat"},
        ),
        event_sink=events.append,
    )
    stop.on_equity(ts("2024-01-02T15:00:00+08:00"), 100_000)
    stop.on_equity(ts("2024-01-02T16:00:00+08:00"), 94_000)
    return stop


def make_req(
    side: OrderSide,
    *,
    created_at: datetime | None = None,
) -> object:
    created_at = created_at or ts("2024-01-04T09:31:00+08:00")
    return type(
        "Req",
        (),
        {
            "order_id": "O-1",
            "strategy_id": "test",
            "account_id": "backtest",
            "symbol": "AAA.SH",
            "side": side,
            "type": OrderType.LIMIT,
            "qty": 100,
            "price": 94,
            "created_at": created_at,
        },
    )()


def make_account(total_value: float) -> Account:
    return Account(
        account_id="backtest",
        currency="CNY",
        cash=100_000,
        frozen=0,
        market_value=0,
        total_value=total_value,
    )


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(TZ)


def write_portfolio_stop_data(tmp_path: Path) -> Path:
    data_root = tmp_path / "portfolio_stop_data"
    data_root.mkdir()
    rows = [
        ("2024-01-02T15:00:00+08:00", 100.0, 100.0),
        ("2024-01-03T15:00:00+08:00", 100.0, 95.0),
        ("2024-01-04T15:00:00+08:00", 94.0, 94.0),
        ("2024-01-05T15:00:00+08:00", 96.0, 96.0),
    ]
    (data_root / "bars_1d.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,pre_close,limit_up,limit_down,suspended,data_status,source,updated_at",
                *[
                    f"AAA.SH,{dt},{open_price},{max(open_price, close_price)},"
                    f"{min(open_price, close_price)},{close_price},1000000,"
                    f"{close_price * 1000000},{open_price},"
                    f"{open_price * 1.1},{open_price * 0.9},False,ok,test,{dt}"
                    for dt, open_price, close_price in rows
                ],
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "instruments.csv").write_text(
        "\n".join(
            [
                "symbol,name,type,exchange,list_date,delist_date,lot_size,qty_step,tick_size,t_plus,status",
                "AAA.SH,Toy Asset,etf,SH,2020-01-01,,100,100,0.001,1,active",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "adjust_factors.csv").write_text(
        "\n".join(
            [
                "symbol,ex_date,factor",
                "AAA.SH,2024-01-02,1.0",
                "AAA.SH,2024-01-03,1.0",
                "AAA.SH,2024-01-04,1.0",
                "AAA.SH,2024-01-05,1.0",
            ]
        ),
        encoding="utf-8",
    )
    return data_root
