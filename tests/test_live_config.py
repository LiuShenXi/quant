from pathlib import Path

import pytest
from pydantic import ValidationError

from quant.core.config import StrategyConfig, load_strategy_config
from quant.live.config import PaperConfig, load_paper_config


def test_strategy_config_accepts_paper_but_rejects_live() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml"))
    assert config.runtime_mode == "paper"
    assert config.risk.max_order_value == 100_000

    with pytest.raises(ValidationError):
        StrategyConfig.model_validate(
            {
                "id": "bad_live",
                "class": "strategies.dual_ma:DualMA",
                "version": "1.0.0",
                "universe": ["510300.SH"],
                "freq": "1d",
                "params": {"symbol": "510300.SH"},
                "runtime_mode": "live",
            }
        )


def test_paper_config_loads_paths_and_thresholds() -> None:
    config: PaperConfig = load_paper_config(Path("config/paper.yaml"))
    assert config.account_id == "paper"
    assert config.store_path.as_posix() == "runtime/paper/meta.db"
    assert config.events_path.as_posix() == "runtime/paper/events.jsonl"
    assert config.reconciliation.cash_tolerance == 0.01
    assert config.monitor.market_data_staleness_sec == 60
