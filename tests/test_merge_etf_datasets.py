from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "merge_etf_datasets.py"
DATA_ROOT = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "data"
)


def test_merge_etf_datasets_combines_single_symbol_roots(tmp_path: Path) -> None:
    out = tmp_path / "merged"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(DATA_ROOT / "etf_510300_20250601_20260626"),
            "--input",
            str(DATA_ROOT / "etf_510500_20250601_20260626"),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "merged data_root" in completed.stdout
    bars = pd.read_csv(out / "bars_1d.csv")
    instruments = pd.read_csv(out / "instruments.csv")
    factors = pd.read_csv(out / "adjust_factors.csv")
    calendar = pd.read_csv(out / "trade_calendar.csv")

    assert len(bars) == 518
    assert sorted(bars["symbol"].unique().tolist()) == ["510300.SH", "510500.SH"]
    assert bars.duplicated(["symbol", "dt"]).sum() == 0
    assert len(instruments) == 2
    assert len(factors) == 518
    assert len(calendar) == 260
