from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RiskMoneyLimit(BaseModel):
    value: float
    unit: Literal["quote_currency", "currency", "equity_pct"]
    currency: str | None = None

    @field_validator("currency")
    @classmethod
    def currency_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("currency must not be empty")
        return value

    @model_validator(mode="after")
    def currency_unit_requires_currency(self) -> "RiskMoneyLimit":
        if self.unit == "currency" and self.currency is None:
            raise ValueError("currency is required when unit is currency")
        return self


class RiskConfig(BaseModel):
    max_order_value: RiskMoneyLimit | float | None = None
    max_position_value: RiskMoneyLimit | float | None = None
    max_gross_exposure_pct: float | None = None
    max_orders_per_minute: int | None = None


class FrequencyConfig(BaseModel):
    primary: str
    history: list[str] = Field(default_factory=list)

    @field_validator("primary")
    @classmethod
    def primary_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("primary frequency must not be empty")
        return value

    @field_validator("history")
    @classmethod
    def history_must_not_include_empty_values(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("history frequencies must not be empty")
        return value

    @model_validator(mode="after")
    def default_history_to_primary(self) -> "FrequencyConfig":
        if not self.history:
            self.history = [self.primary]
        return self


class AccountConfig(BaseModel):
    currency: str = "CNY"
    settlement: str = "t1"
    allow_fractional: bool = False

    @field_validator("currency", "settlement")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class CostConfig(BaseModel):
    model: str | None = None
    preset: str | None = None
    fee_bps: float | None = None
    slippage_bps: float | None = None


class BenchmarkConfig(BaseModel):
    id: str
    type: str
    symbol: str | None = None
    symbols: list[str] = Field(default_factory=list)
    params_patch: dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    class_path: str = Field(alias="class")
    version: str
    universe: list[str]
    freq: str | None = None
    frequencies: FrequencyConfig | None = None
    calendar: str | None = None
    account: AccountConfig = Field(default_factory=AccountConfig)
    params: dict[str, Any]
    risk: RiskConfig = Field(default_factory=RiskConfig)
    costs: CostConfig = Field(default_factory=CostConfig)
    benchmarks: list[BenchmarkConfig] = Field(default_factory=list)
    runtime_mode: Literal["backtest", "paper"]

    @field_validator("universe")
    @classmethod
    def universe_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("universe must not be empty")
        return value

    @field_validator("params")
    @classmethod
    def params_must_not_include_runtime_mode(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "runtime_mode" in value:
            raise ValueError("runtime_mode must not be passed to strategy params")
        return value

    @model_validator(mode="after")
    def normalize_frequencies(self) -> "StrategyConfig":
        if self.frequencies is None:
            if self.freq is None:
                raise ValueError("freq or frequencies.primary is required")
            self.frequencies = FrequencyConfig(primary=self.freq)
        elif self.freq is None:
            self.freq = self.frequencies.primary
        elif self.freq != self.frequencies.primary:
            raise ValueError("freq must match frequencies.primary when both are provided")
        return self

    @property
    def primary_frequency(self) -> str:
        return self.frequencies.primary if self.frequencies is not None else self.freq or ""

    @property
    def history_frequencies(self) -> list[str]:
        if self.frequencies is None:
            return [self.freq] if self.freq is not None else []
        return list(self.frequencies.history)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_strategy_config(path: Path) -> StrategyConfig:
    return StrategyConfig.model_validate(load_yaml(path))
