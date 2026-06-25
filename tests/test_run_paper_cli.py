from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_paper_cli_can_execute_disconnect_drill(tmp_path) -> None:
    paper_config = tmp_path / "paper.yaml"
    events_path = tmp_path / "events.jsonl"
    run_root = tmp_path / "runs"
    paper_config.write_text(
        "\n".join(
            [
                "account_id: paper",
                "initial_cash: 100000",
                "timezone: Asia/Shanghai",
                f"data_root: {Path('data_sample').resolve().as_posix()}",
                f"store_path: {(tmp_path / 'meta.db').as_posix()}",
                f"events_path: {events_path.as_posix()}",
                f"run_root: {run_root.as_posix()}",
                "reconciliation:",
                "  cash_tolerance: 0.01",
                "  position_qty_tolerance: 0",
                "  auto_repair_cash_drift_below: 1.0",
                "monitor:",
                "  market_data_staleness_sec: 60",
                "  gateway_heartbeat_sec: 30",
                "  alert_dedupe_sec: 300",
                "",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_paper.py",
            "--strategy",
            "config/strategies/dual_ma_510300_paper.yaml",
            "--paper",
            str(paper_config),
            "--risk",
            "config/risk/global.yaml",
            "--max-bars",
            "1",
            "--disconnect-drill",
            "--disconnect-reason",
            "network drill",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "disconnect drill:" in completed.stdout
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(event["type"] == "gateway_disconnect" for event in events)
    assert any(event["type"] == "recovery" for event in events)
    assert any(event["type"] == "disconnect_drill" for event in events)
    receipts = list((run_root / "alert_delivery").glob("*.json"))
    assert receipts
