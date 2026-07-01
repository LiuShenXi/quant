from pathlib import Path

import pytest
from pydantic import ValidationError

from quant.data.manifest import DatasetManifest


def _write_manifest(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_dataset_manifest_loads_24x7_multifrequency_metadata(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "dataset_manifest.yaml",
        """
dataset_id: toy_multifreq_24x7_v1
source: test_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2024-01-01T00:00:00Z"
  end: "2024-03-01T00:00:00Z"
symbols:
  - symbol: AAA-USD
    type: spot
    exchange: TEST
    active_from: "2024-01-01T00:00:00Z"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: PT4H
    coverage:
      start: "2024-01-01T00:00:00Z"
      end: "2024-03-01T00:00:00Z"
    construction: source
  - freq: 1d
    file: bars_1d.csv
    expected_interval: P1D
    coverage:
      start: "2024-01-01T00:00:00Z"
      end: "2024-03-01T00:00:00Z"
    construction: aggregate_from_4h
    aggregation:
      source_freq: 4h
      boundary_timezone: UTC
""",
    )

    manifest = DatasetManifest.load(manifest_path)

    assert manifest.dataset_id == "toy_multifreq_24x7_v1"
    assert manifest.calendar == "continuous_24x7"
    assert manifest.timezone == "UTC"
    assert manifest.quote_currency == "USD"
    assert [frequency.freq for frequency in manifest.frequencies] == ["4h", "1d"]
    assert manifest.expected_frequency("4h").file == "bars_4h.csv"
    daily = manifest.expected_frequency("1d")
    assert daily.construction == "aggregate_from_4h"
    assert daily.aggregation == {"source_freq": "4h", "boundary_timezone": "UTC"}


def test_dataset_manifest_respects_symbol_active_window(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "dataset_manifest.yaml",
        """
dataset_id: active_window_fixture
source: test_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2024-01-01T00:00:00Z"
  end: "2024-03-01T00:00:00Z"
symbols:
  - symbol: LATE-USD
    type: spot
    exchange: TEST
    active_from: "2024-02-01T00:00:00Z"
    active_to: "2024-02-20T00:00:00Z"
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: PT4H
    coverage:
      start: "2024-01-01T00:00:00Z"
      end: "2024-03-01T00:00:00Z"
    construction: source
""",
    )

    manifest = DatasetManifest.load(manifest_path)
    symbol = manifest.symbols[0]

    assert symbol.active_from.isoformat() == "2024-02-01T00:00:00+00:00"
    assert symbol.active_to is not None
    assert symbol.active_to.isoformat() == "2024-02-20T00:00:00+00:00"


def test_dataset_manifest_rejects_missing_quote_currency(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "dataset_manifest.yaml",
        """
dataset_id: missing_quote_currency
source: test_fixture
timezone: UTC
calendar: continuous_24x7
coverage:
  start: "2024-01-01T00:00:00Z"
  end: "2024-03-01T00:00:00Z"
symbols:
  - symbol: AAA-USD
    type: spot
    exchange: TEST
    active_from: "2024-01-01T00:00:00Z"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: PT4H
    coverage:
      start: "2024-01-01T00:00:00Z"
      end: "2024-03-01T00:00:00Z"
    construction: source
""",
    )

    with pytest.raises(ValidationError, match="quote_currency"):
        DatasetManifest.load(manifest_path)
