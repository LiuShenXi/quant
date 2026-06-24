from pathlib import Path

from pydantic import BaseModel, Field

from quant.core.config import load_yaml


class ReconciliationConfig(BaseModel):
    cash_tolerance: float = 0.01
    position_qty_tolerance: float = 0
    auto_repair_cash_drift_below: float = 1.0


class MonitorConfig(BaseModel):
    market_data_staleness_sec: int = 60
    gateway_heartbeat_sec: int = 30
    alert_dedupe_sec: int = 300


class PaperConfig(BaseModel):
    account_id: str
    initial_cash: float
    timezone: str = "Asia/Shanghai"
    data_root: Path
    store_path: Path
    events_path: Path
    run_root: Path
    reconciliation: ReconciliationConfig = Field(default_factory=ReconciliationConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)


def load_paper_config(path: Path) -> PaperConfig:
    return PaperConfig.model_validate(load_yaml(path))
