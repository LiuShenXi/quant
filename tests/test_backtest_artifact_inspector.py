from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_backtest_artifacts.py"
REAL_BACKTEST_DIR = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "backtest"
    / "etf_regime_rotation_v1"
)


def test_repo_backtest_inspector_passes_current_research_artifact() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(REAL_BACKTEST_DIR)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["blocking_issues"] == []
    assert payload["files"]["equity"]["rows"] == 518
    assert payload["files"]["events"]["invalid_rows"] == 0
    assert payload["files"]["orders"]["rows"] == 25
    assert payload["files"]["trades"]["rows"] == 25
