from pathlib import Path
from types import ModuleType

import pandas as pd

from quant.backtest.engine import BacktestEngine
from quant.core.config import RiskConfig, load_strategy_config
from quant.core.contract import OrderStatus, StrategyBase
from quant.data.service import DataService


def test_set_target_weight_records_intent_and_submits_next_bar_order(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.target_weight_strategy")

    class TargetWeightStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target_weight(self.symbol, 0.60)

    strategy_module.TargetWeightStrategy = TargetWeightStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.target_weight_strategy" else None,
    )
    config = _target_config(
        class_path="tests.target_weight_strategy:TargetWeightStrategy",
        universe=["AAA-USD"],
        params={"symbol": "AAA-USD"},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=1.0,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD"])),
        initial_cash=100_000,
    ).run()

    target_events = [event for event in result.events if event.event_type == "target_intent"]
    assert len(target_events) == 1
    event = target_events[0]
    assert event.timestamp.isoformat() == "2024-01-02T15:00:00+08:00"
    assert event.payload == {
        "source_bar_timestamp": "2024-01-02T15:00:00+08:00",
        "target_qty": 6_000.0,
        "target_value": 60_000.0,
        "target_weight": 0.60,
        "valuation_price": 10.0,
    }

    assert len(result.orders) == 1
    assert result.orders[0].created_at.isoformat() == "2024-01-03T09:31:00+08:00"
    assert result.orders[0].qty == 6_000.0
    assert result.orders[0].price == 11.0


def test_set_target_weight_uses_total_account_equity_as_denominator(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.target_weight_equity_strategy")

    class TargetWeightEquityStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.calls = 0

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.symbol:
                return
            self.calls += 1
            if self.calls == 1:
                ctx.set_target_weight(self.symbol, 0.50)
            elif self.calls == 2:
                ctx.set_target_weight(self.symbol, 0.60)

    strategy_module.TargetWeightEquityStrategy = TargetWeightEquityStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.target_weight_equity_strategy" else None,
    )
    config = _target_config(
        class_path="tests.target_weight_equity_strategy:TargetWeightEquityStrategy",
        universe=["AAA-USD"],
        params={"symbol": "AAA-USD"},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=1.0,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD"])),
        initial_cash=100_000,
    ).run()

    target_events = [event for event in result.events if event.event_type == "target_intent"]
    assert len(target_events) == 2
    assert target_events[1].payload["target_value"] == 56_991.75
    assert target_events[1].payload["valuation_price"] == 10.0
    assert target_events[1].payload["target_qty"] == 5_699.0


def test_target_weight_batch_over_gross_limit_is_rejected_with_risk_event(
    monkeypatch,
    tmp_path,
) -> None:
    strategy_module = ModuleType("tests.target_weight_over_gross_strategy")

    class TargetWeightOverGrossStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != "AAA-USD" or self.sent:
                return
            self.sent = True
            ctx.set_target_weight("AAA-USD", 0.60)
            ctx.set_target_weight("BBB-USD", 0.50)

    strategy_module.TargetWeightOverGrossStrategy = TargetWeightOverGrossStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.target_weight_over_gross_strategy" else None,
    )
    config = _target_config(
        class_path="tests.target_weight_over_gross_strategy:TargetWeightOverGrossStrategy",
        universe=["AAA-USD", "BBB-USD"],
        params={},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=0.95,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD", "BBB-USD"])),
        initial_cash=100_000,
    ).run()

    assert result.orders == []
    risk_events = [
        event
        for event in result.events
        if event.event_type == "risk_check" and event.risk_rule_id == "gross_exposure"
    ]
    assert len(risk_events) == 1
    assert risk_events[0].payload == {
        "action": "reject_target_batch",
        "allowed": False,
        "batch_gross_weight": 1.10,
        "max_gross_exposure_pct": 0.95,
        "reason": "target weight batch exceeds max gross exposure",
        "target_count": 2,
    }
    rejected_target_events = [
        event for event in result.events if event.event_type == "target_intent_rejected"
    ]
    assert [event.symbol for event in rejected_target_events] == ["AAA-USD", "BBB-USD"]


def test_target_weight_outside_default_long_only_range_is_rejected(
    monkeypatch,
    tmp_path,
) -> None:
    strategy_module = ModuleType("tests.target_weight_out_of_range_strategy")

    class TargetWeightOutOfRangeStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target_weight(self.symbol, 1.01)

    strategy_module.TargetWeightOutOfRangeStrategy = TargetWeightOutOfRangeStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module if name == "tests.target_weight_out_of_range_strategy" else None
        ),
    )
    config = _target_config(
        class_path="tests.target_weight_out_of_range_strategy:TargetWeightOutOfRangeStrategy",
        universe=["AAA-USD"],
        params={"symbol": "AAA-USD"},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=1.0,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD"])),
        initial_cash=100_000,
    ).run()

    assert result.orders == []
    risk_events = [
        event
        for event in result.events
        if event.event_type == "risk_check" and event.risk_rule_id == "target_weight_range"
    ]
    assert len(risk_events) == 1
    assert risk_events[0].payload == {
        "action": "reject_target_intent",
        "allowed": False,
        "reason": "target weight must be between 0.0 and 1.0",
        "target_weight": 1.01,
    }
    rejected_target_events = [
        event for event in result.events if event.event_type == "target_intent_rejected"
    ]
    assert len(rejected_target_events) == 1
    assert rejected_target_events[0].payload["target_weight"] == 1.01


def test_target_weight_fill_is_no_earlier_than_next_bar(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.target_weight_next_bar_strategy")

    class TargetWeightNextBarStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target_weight(self.symbol, 0.60)

    strategy_module.TargetWeightNextBarStrategy = TargetWeightNextBarStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.target_weight_next_bar_strategy" else None,
    )
    config = _target_config(
        class_path="tests.target_weight_next_bar_strategy:TargetWeightNextBarStrategy",
        universe=["AAA-USD"],
        params={"symbol": "AAA-USD"},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=1.0,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD"])),
        initial_cash=100_000,
    ).run()

    assert result.orders[0].created_at.isoformat() == "2024-01-03T09:31:00+08:00"
    assert result.trades[0].dt.isoformat() == "2024-01-03T15:00:00+08:00"
    signal_time = target_event_time(result)
    assert result.orders[0].created_at > signal_time
    assert result.trades[0].dt > signal_time


def test_set_target_value_uses_visible_valuation_price(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.target_value_strategy")

    class TargetValueStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target_value(self.symbol, 12_345.0)

    strategy_module.TargetValueStrategy = TargetValueStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.target_value_strategy" else None,
    )
    config = _target_config(
        class_path="tests.target_value_strategy:TargetValueStrategy",
        universe=["AAA-USD"],
        params={"symbol": "AAA-USD"},
        risk=RiskConfig(
            max_order_value=1_000_000,
            max_position_value=1_000_000,
            max_gross_exposure_pct=1.0,
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_weight_data(tmp_path, ["AAA-USD"])),
        initial_cash=100_000,
    ).run()

    target_events = [event for event in result.events if event.event_type == "target_intent"]
    assert target_events[0].payload["target_value"] == 12_345.0
    assert target_events[0].payload["target_weight"] is None
    assert target_events[0].payload["valuation_price"] == 10.0
    assert target_events[0].payload["target_qty"] == 1_234.0


def target_event_time(result):
    return next(event.timestamp for event in result.events if event.event_type == "target_intent")


def _target_config(*, class_path: str, universe: list[str], params: dict, risk: RiskConfig):
    return load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": class_path,
            "universe": universe,
            "params": params,
            "risk": risk,
        }
    )


def _write_weight_data(tmp_path: Path, symbols: list[str]) -> Path:
    data_root = tmp_path / "weight_data"
    data_root.mkdir()
    rows = []
    for symbol in symbols:
        rows.extend(
            [
                _bar(symbol, "2024-01-02T15:00:00+08:00", open_price=10.0, close_price=10.0),
                _bar(symbol, "2024-01-03T15:00:00+08:00", open_price=11.0, close_price=10.0),
                _bar(symbol, "2024-01-04T15:00:00+08:00", open_price=10.0, close_price=10.0),
            ]
        )
    pd.DataFrame(rows).to_csv(data_root / "bars_1d.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": symbol,
                "name": symbol,
                "type": "crypto",
                "exchange": "TEST",
                "list_date": "2020-01-01",
                "delist_date": "",
                "lot_size": 1,
                "qty_step": 1,
                "tick_size": 0.01,
                "t_plus": 0,
                "status": "active",
            }
            for symbol in symbols
        ]
    ).to_csv(data_root / "instruments.csv", index=False)
    pd.DataFrame(
        [
            {"symbol": symbol, "ex_date": value, "factor": 1.0}
            for symbol in symbols
            for value in ["2024-01-02", "2024-01-03", "2024-01-04"]
        ]
    ).to_csv(data_root / "adjust_factors.csv", index=False)
    return data_root


def _bar(symbol: str, dt: str, *, open_price: float, close_price: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "dt": dt,
        "open": open_price,
        "high": max(open_price, close_price),
        "low": min(open_price, close_price),
        "close": close_price,
        "volume": 1_000_000,
        "amount": close_price * 1_000_000,
        "pre_close": open_price,
        "limit_up": open_price * 2,
        "limit_down": open_price * 0.5,
        "suspended": False,
        "data_status": "ok",
        "source": "test",
        "updated_at": dt,
    }
