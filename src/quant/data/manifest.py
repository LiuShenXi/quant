from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator


class CoverageManifest(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "CoverageManifest":
        if self.end <= self.start:
            raise ValueError("coverage end must be after start")
        return self


class SymbolManifest(BaseModel):
    symbol: str
    type: str
    exchange: str
    active_from: datetime
    active_to: datetime | None = None
    qty_step: float
    lot_size: float
    t_plus: int

    @field_validator("symbol", "type", "exchange")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def active_to_must_follow_active_from(self) -> "SymbolManifest":
        if self.active_to is not None and self.active_to <= self.active_from:
            raise ValueError("active_to must be after active_from")
        return self


class FrequencyManifest(BaseModel):
    freq: str
    file: str
    expected_interval: str
    coverage: CoverageManifest
    construction: str
    aggregation: dict[str, Any] | None = None

    @field_validator("freq", "file", "expected_interval", "construction")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class DatasetManifest(BaseModel):
    dataset_id: str
    source: str
    timezone: str
    calendar: str
    quote_currency: str
    coverage: CoverageManifest
    symbols: list[SymbolManifest]
    frequencies: list[FrequencyManifest]

    @classmethod
    def load(cls, path: Path) -> "DatasetManifest":
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        return cls.model_validate(data)

    def expected_frequency(self, freq: str) -> FrequencyManifest:
        for frequency in self.frequencies:
            if frequency.freq == freq:
                return frequency
        raise ValueError(f"frequency {freq!r} is not declared in dataset manifest")

    @field_validator("dataset_id", "source", "timezone", "calendar", "quote_currency")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("symbols", "frequencies")
    @classmethod
    def list_must_not_be_empty(cls, value: list[Any]) -> list[Any]:
        if not value:
            raise ValueError("must not be empty")
        return value
