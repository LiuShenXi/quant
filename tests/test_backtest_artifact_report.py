from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_backtest_artifacts.py"
REAL_BACKTEST_DIR = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "backtest"
    / "etf_regime_rotation_v1"
)


def test_repo_backtest_report_summarizes_current_research_artifact() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(REAL_BACKTEST_DIR)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["not_trading_permission"] is True
    assert payload["artifact_dir"] == str(REAL_BACKTEST_DIR)
    assert payload["period"] == {
        "start": "2025-06-03T15:00:00+08:00",
        "end": "2026-06-25T15:00:00+08:00",
        "equity_rows": 518,
    }
    assert payload["metrics"]["initial_value"] == 100000.0
    assert payload["metrics"]["final_value"] == 120098.3
    assert payload["metrics"]["return_pct"] == 20.0983
    assert payload["metrics"]["max_drawdown_pct"] == -6.4892
    assert payload["orders"]["rows"] == 25
    assert payload["orders"]["rejected"] == 0
    assert payload["trades"]["rows"] == 25
    assert payload["trades"]["symbols"] == ["510300.SH", "510500.SH"]
    assert payload["costs"]["total_commission"] == 553.7
    assert payload["hashes"]["equity.csv"]
    assert payload["hashes"]["orders.csv"]
