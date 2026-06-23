from pathlib import Path

from quant.backtest.engine import BacktestEngine
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
