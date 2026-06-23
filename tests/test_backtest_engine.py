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
