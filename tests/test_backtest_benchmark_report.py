from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_backtest_benchmarks.py"
DATA_ROOT = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "data"
    / "etf_rotation_510300_510500_20250601_20260626"
)


def test_repo_benchmark_report_summarizes_research_dataset() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(DATA_ROOT), "--symbols", "510300.SH", "510500.SH"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["not_trading_permission"] is True
    assert payload["data_root"] == str(DATA_ROOT)
    assert payload["method"] == "close_to_close_normalized_buy_and_hold"
    assert payload["benchmarks"]["510300.SH"]["return_pct"] == 27.5714
    assert payload["benchmarks"]["510300.SH"]["max_drawdown_pct"] == -9.941
    assert payload["benchmarks"]["510500.SH"]["return_pct"] == 59.3021
    assert payload["benchmarks"]["510500.SH"]["max_drawdown_pct"] == -14.0208
    assert payload["benchmarks"]["equal_weight"]["return_pct"] == 43.4368
    assert payload["benchmarks"]["equal_weight"]["max_drawdown_pct"] == -10.7071
    assert payload["benchmarks"]["equal_weight"]["symbols"] == ["510300.SH", "510500.SH"]
    assert payload["period"] == {
        "start": "2025-06-03T15:00:00+08:00",
        "end": "2026-06-25T15:00:00+08:00",
        "rows": 259,
    }
