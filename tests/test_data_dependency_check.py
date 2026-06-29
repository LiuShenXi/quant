from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_data_dependencies.py"


def test_data_dependency_check_reports_present_and_missing_modules() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--module",
            "pandas",
            "--module",
            "definitely_missing_quant_data_dependency",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["status"] == "FAIL"
    assert payload["modules"]["pandas"]["available"] is True
    assert payload["modules"]["definitely_missing_quant_data_dependency"]["available"] is False
