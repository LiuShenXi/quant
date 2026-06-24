from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from quant.core.config import load_yaml


class ReconciliationConfig(BaseModel):
    cash_tolerance: float = 0.01
    position_qty_tolerance: float = 0
    auto_repair_cash_drift_below: float = 1.0


class MonitorConfig(BaseModel):
    market_data_staleness_sec: int = 60
    gateway_heartbeat_sec: int = 30
    alert_dedupe_sec: int = 300


class KillSwitchConfig(BaseModel):
    daily_loss_freeze_pct: float = 0.02
    daily_loss_halt_pct: float = 0.04


class GlobalRiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    whitelist_mode: bool
    price_collar_pct: float
    max_order_value: float | None = None
    max_position_value_per_symbol: float | None = None
    max_gross_exposure_pct: float | None = None
    max_orders_per_minute: int | None = None
    max_cancel_ratio_daily: float | None = None
    kill_switch: KillSwitchConfig = Field(default_factory=KillSwitchConfig)
    market_data_staleness_sec: int = 60


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


def load_global_risk_config(path: Path) -> GlobalRiskConfig:
    return GlobalRiskConfig.model_validate(load_yaml(path))
