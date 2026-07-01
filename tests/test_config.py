from pathlib import Path

import pytest
from pydantic import ValidationError

from quant.core.config import RiskMoneyLimit, StrategyConfig, load_strategy_config


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


def test_strategy_config_accepts_class_path_field_name() -> None:
    config = StrategyConfig(
        id="ok",
        class_path="strategies.dual_ma:DualMA",
        version="1.0.0",
        universe=["510300.SH"],
        freq="1d",
        params={"symbol": "510300.SH"},
        runtime_mode="backtest",
    )
    assert config.class_path == "strategies.dual_ma:DualMA"


def test_legacy_freq_maps_to_primary_frequency() -> None:
    config = StrategyConfig(
        id="legacy",
        class_path="strategies.dual_ma:DualMA",
        version="1.0.0",
        universe=["510300.SH"],
        freq="1d",
        params={"symbol": "510300.SH"},
        runtime_mode="backtest",
    )

    assert config.freq == "1d"
    assert config.primary_frequency == "1d"
    assert config.history_frequencies == ["1d"]


def test_strategy_config_accepts_multifrequency_account_and_runtime_mode() -> None:
    config = StrategyConfig.model_validate(
        {
            "id": "research_slice",
            "class": "strategies.example:ExampleStrategy",
            "version": "1.0.0",
            "universe": ["AAA-USD", "BBB-USD"],
            "frequencies": {"primary": "4h", "history": ["1d", "4h"]},
            "calendar": "continuous_24x7",
            "account": {
                "currency": "USD",
                "settlement": "t0",
                "allow_fractional": True,
            },
            "params": {"lookback": 20},
            "risk": {
                "max_position_value": {
                    "value": 60_000,
                    "unit": "quote_currency",
                    "currency": "USD",
                }
            },
            "runtime_mode": "backtest",
        }
    )

    assert config.freq == "4h"
    assert config.primary_frequency == "4h"
    assert config.history_frequencies == ["1d", "4h"]
    assert config.account.currency == "USD"
    assert config.account.settlement == "t0"
    assert config.account.allow_fractional is True
    assert config.risk.max_position_value.value == 60_000
    assert config.risk.max_position_value.unit == "quote_currency"
    assert config.runtime_mode == "backtest"


def test_strategy_config_rejects_money_limit_dict_without_unit() -> None:
    try:
        StrategyConfig.model_validate(
            {
                "id": "bad_risk",
                "class": "strategies.example:ExampleStrategy",
                "version": "1.0.0",
                "universe": ["AAA-USD"],
                "frequencies": {"primary": "4h"},
                "params": {},
                "risk": {"max_order_value": {"value": 10_000}},
                "runtime_mode": "backtest",
            }
        )
    except ValidationError as exc:
        assert "unit" in str(exc)
    else:
        raise AssertionError("money risk limit dicts must declare unit")


def test_strategy_config_exposes_costs_and_benchmarks_defaults() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))

    assert config.costs.model is None
    assert config.costs.fee_bps is None
    assert config.costs.slippage_bps is None
    assert config.benchmarks == []


def test_strategy_config_retains_costs_and_benchmarks_surface() -> None:
    config = StrategyConfig.model_validate(
        {
            "id": "research_slice",
            "class": "strategies.example:ExampleStrategy",
            "version": "1.0.0",
            "universe": ["AAA-USD", "BBB-USD"],
            "frequencies": {"primary": "4h"},
            "params": {},
            "risk": {},
            "costs": {
                "model": "bps",
                "preset": "baseline",
                "fee_bps": 10,
                "slippage_bps": 20,
            },
            "benchmarks": [
                {"id": "cash", "type": "cash"},
                {
                    "id": "buy_hold_AAA",
                    "type": "single_asset_buy_hold",
                    "symbol": "AAA-USD",
                },
                {
                    "id": "equal_weight_universe",
                    "type": "equal_weight_buy_hold",
                    "symbols": ["AAA-USD", "BBB-USD"],
                },
                {
                    "id": "ablation_no_stop",
                    "type": "strategy_variant",
                    "params_patch": {"risk.portfolio_stop.enabled": False},
                },
            ],
            "runtime_mode": "backtest",
        }
    )

    assert config.costs.model == "bps"
    assert config.costs.preset == "baseline"
    assert config.costs.fee_bps == 10
    assert config.costs.slippage_bps == 20
    assert config.benchmarks[0].id == "cash"
    assert config.benchmarks[1].symbol == "AAA-USD"
    assert config.benchmarks[2].symbols == ["AAA-USD", "BBB-USD"]
    assert config.benchmarks[3].params_patch == {
        "risk.portfolio_stop.enabled": False
    }

    dumped = config.model_dump(mode="json", by_alias=True)
    assert dumped["costs"]["model"] == "bps"
    assert dumped["benchmarks"][3]["params_patch"] == {
        "risk.portfolio_stop.enabled": False
    }


def test_risk_money_limit_requires_currency_when_unit_is_currency() -> None:
    with pytest.raises(ValidationError, match="currency"):
        RiskMoneyLimit(value=10_000, unit="currency")
