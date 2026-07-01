import filecmp
import shutil
from pathlib import Path
from types import ModuleType

import pandas as pd

from quant.backtest.engine import BacktestEngine
from quant.backtest.results import write_result
from quant.core.config import RiskConfig, load_strategy_config
from quant.core.contract import OrderSide, OrderStatus, StrategyBase
from quant.data.service import DataService


def test_engine_runs_dual_ma_and_produces_deterministic_trades() -> None:
    config = _active_sample_config()
    data = DataService(Path("data_sample"))
    first = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    second = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    assert [trade.__dict__ for trade in first.trades] == [trade.__dict__ for trade in second.trades]
    assert len(first.orders) >= 1
    assert len(first.equity) >= 1


def test_engine_keeps_partially_filled_order_open() -> None:
    config = _active_sample_config().model_copy(
        update={
            "params": {"symbol": "510300.SH", "fast": 1, "slow": 2, "target_qty": 100000},
            "risk": RiskConfig(
                max_order_value=500_000,
                max_position_value=500_000,
                max_gross_exposure_pct=10,
            ),
        }
    )
    data = DataService(Path("data_sample"))
    result = BacktestEngine(config=config, data=data, initial_cash=1_000_000).run()
    partial_orders = [order for order in result.orders if order.status.value == "PARTIAL"]
    assert partial_orders
    assert partial_orders[0].remaining_qty > 0


def test_set_target_counts_active_orders_before_submitting_more(monkeypatch, tmp_path) -> None:
    strategy_module = ModuleType("tests.backtest_repeat_target_strategy")

    class RepeatTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])
            self.calls = 0

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.symbol or self.calls >= 2:
                return
            self.calls += 1
            ctx.set_target(self.symbol, self.target_qty)

    strategy_module.RepeatTargetStrategy = RepeatTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.backtest_repeat_target_strategy" else None,
    )
    data_root = _copy_sample_data_with_volume(tmp_path, volume=1_000)
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_repeat_target_strategy:RepeatTargetStrategy",
            "params": {"symbol": "510300.SH", "target_qty": 10_000},
        }
    )

    result = BacktestEngine(config=config, data=DataService(data_root), initial_cash=100_000).run()

    active_or_filled_buys = [
        order
        for order in result.orders
        if order.side.value == "BUY" and order.status != OrderStatus.REJECTED
    ]
    assert len(active_or_filled_buys) == 1
    assert active_or_filled_buys[0].qty == 10_000


def test_set_target_buy_rejected_when_it_exceeds_backtest_risk(monkeypatch) -> None:
    strategy_module = ModuleType("tests.backtest_oversized_target_strategy")

    class OversizedTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target(self.symbol, self.target_qty)

    strategy_module.OversizedTargetStrategy = OversizedTargetStrategy

    def fake_import_module(name: str):
        if name == "tests.backtest_oversized_target_strategy":
            return strategy_module
        return None

    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        fake_import_module,
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_oversized_target_strategy:OversizedTargetStrategy",
            "params": {"symbol": "510300.SH", "target_qty": 10_000},
            "risk": RiskConfig(max_position_value=5_000),
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    assert len(result.orders) == 1
    assert result.orders[0].status == OrderStatus.REJECTED
    assert result.orders[0].reject_reason == (
        "position_limit: projected symbol position exceeds limit"
    )
    assert result.trades == []


def test_set_target_splits_orders_to_respect_single_order_limit(monkeypatch) -> None:
    strategy_module = ModuleType("tests.backtest_large_target_strategy")

    class LargeTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.target_qty = float(ctx.params["target_qty"])
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target(self.symbol, self.target_qty)

    strategy_module.LargeTargetStrategy = LargeTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.backtest_large_target_strategy" else None,
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_large_target_strategy:LargeTargetStrategy",
            "params": {"symbol": "510300.SH", "target_qty": 10_000},
            "risk": RiskConfig(
                max_order_value=10_000,
                max_position_value=100_000,
                max_gross_exposure_pct=1,
            ),
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    buy_orders = [order for order in result.orders if order.side == OrderSide.BUY]
    assert len(buy_orders) > 1
    assert all(order.status != OrderStatus.REJECTED for order in buy_orders)
    assert all(order.qty * float(order.price) <= 10_000 for order in buy_orders)
    assert sum(order.qty for order in buy_orders) == 10_000


def test_target_created_from_one_symbol_close_waits_until_next_day_open(
    monkeypatch,
    tmp_path,
) -> None:
    strategy_module = ModuleType("tests.backtest_cross_symbol_target_strategy")

    class CrossSymbolTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.signal_symbol = ctx.params["signal_symbol"]
            self.target_symbol = ctx.params["target_symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.signal_symbol and not self.sent:
                self.sent = True
                ctx.set_target(self.target_symbol, 100)

    strategy_module.CrossSymbolTargetStrategy = CrossSymbolTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module if name == "tests.backtest_cross_symbol_target_strategy" else None
        ),
    )
    data_root = _write_two_symbol_data(tmp_path)
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_cross_symbol_target_strategy:CrossSymbolTargetStrategy",
            "universe": ["AAA.SH", "BBB.SH"],
            "params": {"signal_symbol": "AAA.SH", "target_symbol": "BBB.SH"},
            "risk": RiskConfig(
                max_order_value=500_000,
                max_position_value=500_000,
                max_gross_exposure_pct=10,
            ),
        }
    )

    result = BacktestEngine(config=config, data=DataService(data_root), initial_cash=100_000).run()

    assert len(result.orders) == 1
    assert result.orders[0].symbol == "BBB.SH"
    assert result.orders[0].created_at.isoformat() == "2024-01-03T09:31:00+08:00"
    assert len(result.trades) == 1
    assert result.trades[0].symbol == "BBB.SH"
    assert result.trades[0].price == 21.0


def test_daily_multi_symbol_close_callbacks_see_session_open_fills_and_close_marks(
    monkeypatch,
    tmp_path,
) -> None:
    strategy_module = ModuleType("tests.backtest_daily_session_strategy")
    observations = []

    class DailySessionStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.signal_symbol = ctx.params["signal_symbol"]
            self.target_symbol = ctx.params["target_symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.signal_symbol:
                return
            position = ctx.get_position(self.target_symbol)
            observations.append(
                {
                    "dt": ctx.now.isoformat(),
                    "target_qty": position.qty,
                    "account_total": ctx.get_account().total_value,
                }
            )
            if not self.sent:
                self.sent = True
                ctx.set_target(self.target_symbol, 100)

    strategy_module.DailySessionStrategy = DailySessionStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.backtest_daily_session_strategy" else None,
    )
    data_root = _write_two_symbol_data(tmp_path)
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_daily_session_strategy:DailySessionStrategy",
            "universe": ["AAA.SH", "BBB.SH"],
            "params": {"signal_symbol": "AAA.SH", "target_symbol": "BBB.SH"},
            "risk": RiskConfig(
                max_order_value=500_000,
                max_position_value=500_000,
                max_gross_exposure_pct=10,
            ),
        }
    )

    result = BacktestEngine(config=config, data=DataService(data_root), initial_cash=100_000).run()

    assert len(result.equity) == 2
    assert [row["dt"] for row in result.equity] == [
        "2024-01-02T15:00:00+08:00",
        "2024-01-03T15:00:00+08:00",
    ]
    assert observations[1] == {
        "dt": "2024-01-03T15:00:00+08:00",
        "target_qty": 100,
        "account_total": 100045.0,
    }


def test_set_target_sell_rejected_without_sellable_position(monkeypatch) -> None:
    strategy_module = ModuleType("tests.backtest_negative_target_strategy")

    class NegativeTargetStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target(self.symbol, -100)

    strategy_module.NegativeTargetStrategy = NegativeTargetStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.backtest_negative_target_strategy" else None,
    )
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": "tests.backtest_negative_target_strategy:NegativeTargetStrategy",
            "params": {"symbol": "510300.SH"},
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    assert len(result.orders) == 1
    assert result.orders[0].status == OrderStatus.REJECTED
    assert result.orders[0].reject_reason == "cash: insufficient sellable position for sell order"
    assert result.trades == []


def test_engine_rejects_universe_with_missing_data() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "universe": ["159999.SZ"],
            "params": {"symbol": "159999.SZ", "fast": 3, "slow": 5, "target_qty": 100},
        }
    )
    data = DataService(Path("data_sample"))
    try:
        BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("backtest must reject missing data in universe")


def test_write_result_artifacts(tmp_path) -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    data = DataService(Path("data_sample"))
    result = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    write_result(result, output_dir=tmp_path, config=config)
    assert (tmp_path / "config_snapshot.yaml").exists()
    assert (tmp_path / "orders.csv").exists()
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "equity.csv").exists()
    assert (tmp_path / "events.jsonl").exists()
    assert (tmp_path / "report.md").exists()


def test_golden_regression(tmp_path) -> None:
    config = _active_sample_config()
    data = DataService(Path("data_sample"))
    result = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    write_result(result, output_dir=tmp_path, config=config)
    assert filecmp.cmp(tmp_path / "orders.csv", Path("tests/golden/orders.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "trades.csv", Path("tests/golden/trades.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "equity.csv", Path("tests/golden/equity.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "events.jsonl", Path("tests/golden/events.jsonl"), shallow=False)


def _copy_sample_data_with_volume(tmp_path: Path, *, volume: float) -> Path:
    data_root = tmp_path / "data"
    shutil.copytree(Path("data_sample"), data_root)
    bars_path = data_root / "bars_1d.csv"
    bars = pd.read_csv(bars_path)
    bars.loc[bars["symbol"] == "510300.SH", "volume"] = volume
    bars.to_csv(bars_path, index=False)
    return data_root


def _write_two_symbol_data(tmp_path: Path) -> Path:
    data_root = tmp_path / "two_symbol_data"
    data_root.mkdir()
    rows = []
    for symbol, open_price, close_price in [
        ("AAA.SH", 10.0, 10.5),
        ("BBB.SH", 20.0, 20.5),
    ]:
        rows.extend(
            [
                {
                    "symbol": symbol,
                    "dt": "2024-01-02T15:00:00+08:00",
                    "open": open_price,
                    "high": close_price,
                    "low": open_price,
                    "close": close_price,
                    "volume": 1_000_000,
                    "amount": close_price * 1_000_000,
                    "pre_close": open_price,
                    "limit_up": open_price * 1.1,
                    "limit_down": open_price * 0.9,
                    "suspended": False,
                    "data_status": "ok",
                    "source": "test",
                    "updated_at": "2024-01-02T17:00:00+08:00",
                },
                {
                    "symbol": symbol,
                    "dt": "2024-01-03T15:00:00+08:00",
                    "open": open_price + 1,
                    "high": close_price + 1,
                    "low": open_price + 1,
                    "close": close_price + 1,
                    "volume": 1_000_000,
                    "amount": (close_price + 1) * 1_000_000,
                    "pre_close": close_price,
                    "limit_up": close_price * 1.1,
                    "limit_down": close_price * 0.9,
                    "suspended": False,
                    "data_status": "ok",
                    "source": "test",
                    "updated_at": "2024-01-03T17:00:00+08:00",
                },
            ]
        )
    pd.DataFrame(rows).to_csv(data_root / "bars_1d.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "AAA.SH",
                "name": "Signal ETF",
                "type": "etf",
                "exchange": "SH",
                "list_date": "2020-01-01",
                "delist_date": "",
                "lot_size": 100,
                "qty_step": 100,
                "tick_size": 0.001,
                "t_plus": 1,
                "status": "active",
            },
            {
                "symbol": "BBB.SH",
                "name": "Target ETF",
                "type": "etf",
                "exchange": "SH",
                "list_date": "2020-01-01",
                "delist_date": "",
                "lot_size": 100,
                "qty_step": 100,
                "tick_size": 0.001,
                "t_plus": 1,
                "status": "active",
            },
        ]
    ).to_csv(data_root / "instruments.csv", index=False)
    pd.DataFrame(
        [
            {"symbol": "AAA.SH", "ex_date": "2024-01-02", "factor": 1.0},
            {"symbol": "AAA.SH", "ex_date": "2024-01-03", "factor": 1.0},
            {"symbol": "BBB.SH", "ex_date": "2024-01-02", "factor": 1.0},
            {"symbol": "BBB.SH", "ex_date": "2024-01-03", "factor": 1.0},
        ]
    ).to_csv(data_root / "adjust_factors.csv", index=False)
    return data_root


def _active_sample_config():
    return load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={"params": {"symbol": "510300.SH", "fast": 1, "slow": 2, "target_qty": 10000}}
    )
