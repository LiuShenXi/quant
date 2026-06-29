from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_backtest_sample_splits.py"
ARTIFACT_DIR = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "backtest"
    / "etf_regime_rotation_v1"
)
DATA_ROOT = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "data"
    / "etf_rotation_510300_510500_20250601_20260626"
)


def test_sample_split_report_summarizes_strategy_and_benchmarks() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(ARTIFACT_DIR),
            str(DATA_ROOT),
            "--symbols",
            "510300.SH",
            "510500.SH",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["not_trading_permission"] is True
    assert payload["method"] == "unique_date_halves_daily_last_equity"
    assert payload["splits"]["first_half"]["period"]["rows"] == 129
    assert payload["splits"]["first_half"]["period"]["end"] == "2025-12-08T15:00:00+08:00"
    assert payload["splits"]["first_half"]["strategy"]["return_pct"] == 1.3941
    assert payload["splits"]["first_half"]["strategy"]["max_drawdown_pct"] == -5.7348
    assert payload["splits"]["first_half"]["benchmarks"]["equal_weight"]["return_pct"] == 23.6013
    assert payload["splits"]["second_half"]["period"]["rows"] == 130
    assert payload["splits"]["second_half"]["period"]["start"] == "2025-12-09T15:00:00+08:00"
    assert payload["splits"]["second_half"]["strategy"]["return_pct"] == 18.9313
    assert payload["splits"]["second_half"]["benchmarks"]["equal_weight"]["return_pct"] == 16.4916
    assert payload["splits"]["second_half"]["benchmarks"]["510500.SH"]["return_pct"] == 25.7614
