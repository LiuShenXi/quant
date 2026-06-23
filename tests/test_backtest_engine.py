import filecmp
from pathlib import Path

from quant.backtest.engine import BacktestEngine
from quant.backtest.results import write_result
from quant.core.config import load_strategy_config
from quant.data.service import DataService


def test_engine_runs_dual_ma_and_produces_deterministic_trades() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    data = DataService(Path("data_sample"))
    first = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    second = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    assert [trade.__dict__ for trade in first.trades] == [trade.__dict__ for trade in second.trades]
    assert len(first.orders) >= 1
    assert len(first.equity) >= 1


def test_engine_keeps_partially_filled_order_open() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={"params": {"symbol": "510300.SH", "fast": 1, "slow": 2, "target_qty": 100000}}
    )
    data = DataService(Path("data_sample"))
    result = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    partial_orders = [order for order in result.orders if order.status.value == "PARTIAL"]
    assert partial_orders
    assert partial_orders[0].remaining_qty > 0


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
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    data = DataService(Path("data_sample"))
    result = BacktestEngine(config=config, data=data, initial_cash=100_000).run()
    write_result(result, output_dir=tmp_path, config=config)
    assert filecmp.cmp(tmp_path / "orders.csv", Path("tests/golden/orders.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "trades.csv", Path("tests/golden/trades.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "equity.csv", Path("tests/golden/equity.csv"), shallow=False)
    assert filecmp.cmp(tmp_path / "events.jsonl", Path("tests/golden/events.jsonl"), shallow=False)
