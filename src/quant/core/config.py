from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskConfig(BaseModel):
    max_order_value: float | None = None
    max_position_value: float | None = None


class StrategyConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    class_path: str = Field(alias="class")
    version: str
    universe: list[str]
    freq: Literal["1d"]
    params: dict[str, Any]
    risk: RiskConfig = Field(default_factory=RiskConfig)
    runtime_mode: Literal["backtest"]

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


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_strategy_config(path: Path) -> StrategyConfig:
    return StrategyConfig.model_validate(load_yaml(path))
