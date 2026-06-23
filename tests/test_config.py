from pathlib import Path

from pydantic import ValidationError

from quant.core.config import StrategyConfig, load_strategy_config


def test_strategy_config_loads_runtime_mode_outside_params() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    assert config.id == "dual_ma_510300"
    assert config.runtime_mode == "backtest"
    assert "runtime_mode" not in config.params


def test_strategy_config_rejects_empty_universe() -> None:
    try:
        StrategyConfig(
            id="bad",
            class_path="strategies.dual_ma:DualMA",
            version="1.0.0",
            universe=[],
            freq="1d",
            params={"symbol": "510300.SH"},
            runtime_mode="backtest",
        )
    except ValidationError as exc:
        assert "universe" in str(exc)
    else:
        raise AssertionError("empty universe must fail")
