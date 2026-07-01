from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from quant.data.service import DataService


UTC = ZoneInfo("UTC")


def test_load_bars_uses_manifest_frequency_file_and_sets_bar_frequency(tmp_path: Path) -> None:
    data_root = _write_manifest_dataset(tmp_path)
    service = DataService(data_root)

    bars = service.load_bars(["AAA-USD"], freq="4h")

    assert [bar.freq for bar in bars] == ["4h", "4h", "4h", "4h"]
    assert [bar.dt for bar in bars] == [
        datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 4, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    ]
    assert service.latest_bar_time("AAA-USD", freq="4h") == datetime(
        2024, 1, 1, 12, 0, tzinfo=UTC
    )


def test_history_filters_multifrequency_rows_to_closed_bars_at_or_before_end(
    tmp_path: Path,
) -> None:
    data_root = _write_manifest_dataset(tmp_path)
    service = DataService(data_root)

    history = service.history(
        symbol="AAA-USD",
        end=datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
        n=3,
        freq="4h",
    )

    assert history["dt"].tolist() == [
        pd.Timestamp("2024-01-01T00:00:00Z"),
        pd.Timestamp("2024-01-01T04:00:00Z"),
        pd.Timestamp("2024-01-01T08:00:00Z"),
    ]
    assert history["dt"].max() <= datetime(2024, 1, 1, 8, 0, tzinfo=UTC)


def test_missing_active_window_multifrequency_bars_fail_deterministically(
    tmp_path: Path,
) -> None:
    bars_4h = _bars_for("AAA-USD")
    bars_4h = bars_4h[bars_4h["dt"] != "2024-01-01T08:00:00+00:00"]
    data_root = _write_manifest_dataset(tmp_path, bars_4h=bars_4h)
    service = DataService(data_root)

    with pytest.raises(ValueError, match="AAA-USD.*2024-01-01T08:00:00\\+00:00"):
        service.load_bars(["AAA-USD"], freq="4h")


def test_multifrequency_completeness_ignores_timestamps_before_symbol_active_from(
    tmp_path: Path,
) -> None:
    bars_4h = _bars_for("LATE-USD").iloc[2:].reset_index(drop=True)
    data_root = _write_manifest_dataset(
        tmp_path,
        symbol="LATE-USD",
        active_from="2024-01-01T08:00:00Z",
        bars_4h=bars_4h,
    )
    service = DataService(data_root)

    bars = service.load_bars(["LATE-USD"], freq="4h")

    assert [bar.dt for bar in bars] == [
        datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    ]


def _write_manifest_dataset(
    tmp_path: Path,
    *,
    symbol: str = "AAA-USD",
    active_from: str = "2024-01-01T00:00:00Z",
    bars_4h: pd.DataFrame | None = None,
) -> Path:
    data_root = tmp_path / "dataset"
    data_root.mkdir()
    bars = _bars_for(symbol) if bars_4h is None else bars_4h
    bars.to_csv(data_root / "bars_4h.csv", index=False)
    _daily_bars_for(symbol).to_csv(data_root / "bars_1d.csv", index=False)
    _instruments_for(symbol).to_csv(data_root / "instruments.csv", index=False)
    pd.DataFrame([{"symbol": symbol, "ex_date": "2024-01-01", "factor": 1.0}]).to_csv(
        data_root / "adjust_factors.csv", index=False
    )
    (data_root / "dataset_manifest.yaml").write_text(
        f"""
dataset_id: test_multifrequency
source: test_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2024-01-01T00:00:00Z"
  end: "2024-01-01T12:00:00Z"
symbols:
  - symbol: {symbol}
    type: spot
    exchange: TEST
    active_from: "{active_from}"
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
      end: "2024-01-01T12:00:00Z"
    construction: source
  - freq: 1d
    file: bars_1d.csv
    expected_interval: P1D
    coverage:
      start: "2024-01-01T00:00:00Z"
      end: "2024-01-02T00:00:00Z"
    construction: aggregate_from_4h
    aggregation:
      source_freq: 4h
      boundary_timezone: UTC
""",
        encoding="utf-8",
    )
    return data_root


def _bars_for(symbol: str) -> pd.DataFrame:
    rows = []
    for hour, close in [(0, 100.0), (4, 104.0), (8, 108.0), (12, 112.0)]:
        rows.append(
            {
                "symbol": symbol,
                "dt": f"2024-01-01T{hour:02d}:00:00+00:00",
                "open": close - 1.0,
                "high": close + 1.0,
                "low": close - 2.0,
                "close": close,
                "volume": 10.0 + hour,
                "amount": 1000.0 + hour,
                "pre_close": close - 4.0,
                "limit_up": "",
                "limit_down": "",
                "suspended": False,
                "data_status": "ok",
                "source": "test",
                "updated_at": "2024-01-01T13:00:00+00:00",
            }
        )
    return pd.DataFrame(rows)


def _daily_bars_for(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "dt": "2024-01-01T00:00:00+00:00",
                "open": 99.0,
                "high": 113.0,
                "low": 98.0,
                "close": 112.0,
                "volume": 100.0,
                "amount": 10000.0,
                "pre_close": 99.0,
                "limit_up": "",
                "limit_down": "",
                "suspended": False,
                "data_status": "ok",
                "source": "test",
                "updated_at": "2024-01-01T13:00:00+00:00",
            }
        ]
    )


def _instruments_for(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "name": symbol,
                "type": "spot",
                "exchange": "TEST",
                "list_date": "2024-01-01",
                "delist_date": "",
                "lot_size": 1,
                "qty_step": 1,
                "tick_size": 0.01,
                "t_plus": 0,
                "status": "active",
            }
        ]
    )
