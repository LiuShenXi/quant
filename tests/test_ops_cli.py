import json
import subprocess
import sys

from quant.live.store import OmsStore
from quant.live.types import EngineState


def test_ops_cli_halt_resume_and_status(tmp_path) -> None:
    store_path = tmp_path / "meta.db"
    events_path = tmp_path / "events.jsonl"
    OmsStore(store_path).init_schema()

    halt = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "halt",
            "--reason",
            "manual drill",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert halt.returncode == 0, halt.stdout + halt.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.HALT

    status = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "status",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert status.returncode == 0, status.stdout + status.stderr
    assert "HALT" in status.stdout
    assert "ops_action" in events_path.read_text(encoding="utf-8")

    resume = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "resume",
            "--reason",
            "checked account and positions",
            "--precheck",
            "account",
            "--precheck",
            "positions",
            "--precheck",
            "active_orders",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert resume.returncode == 0, resume.stdout + resume.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.NORMAL


def test_ops_cli_freeze_open_preserves_halt_and_audits_attempt(tmp_path) -> None:
    store_path = tmp_path / "meta.db"
    events_path = tmp_path / "events.jsonl"
    OmsStore(store_path).init_schema()
    OmsStore(store_path).set_engine_state(EngineState.HALT, "manual drill")

    freeze_open = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "freeze-open",
            "--reason",
            "stale data drill",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert freeze_open.returncode == 0, freeze_open.stdout + freeze_open.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.HALT
    event = json.loads(events_path.read_text(encoding="utf-8").strip())
    assert event["type"] == "ops_action"
    assert event["payload"]["state"] == EngineState.HALT.value
    assert event["payload"]["action"] == "preserve_halt"


def test_ops_cli_resume_requires_all_prechecks(tmp_path) -> None:
    store_path = tmp_path / "meta.db"
    events_path = tmp_path / "events.jsonl"
    OmsStore(store_path).init_schema()
    OmsStore(store_path).set_engine_state(EngineState.HALT, "manual drill")

    resume = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "resume",
            "--reason",
            "checked account and positions",
            "--precheck",
            "account",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert resume.returncode != 0
    assert "resume missing precheck" in resume.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.HALT
