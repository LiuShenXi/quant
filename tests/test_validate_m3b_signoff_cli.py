from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

TRADING_DATES = [
    "2024-01-02",
    "2024-01-03",
    "2024-01-04",
    "2024-01-05",
    "2024-01-08",
    "2024-01-09",
    "2024-01-10",
    "2024-01-11",
    "2024-01-12",
    "2024-01-15",
]


def test_validate_m3b_signoff_cli_accepts_complete_operator_artifact(tmp_path) -> None:
    signoff_path = _write_complete_signoff_package(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_m3b_signoff.py",
            str(signoff_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "M3b signoff validated" in completed.stdout
    assert "M4a may start" in completed.stdout


def test_validate_m3b_signoff_cli_rejects_incomplete_template(tmp_path) -> None:
    signoff_path = tmp_path / "m3b_signoff.yaml"
    signoff_path.write_text(
        Path("docs/runbooks/m3b_signoff_template.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_m3b_signoff.py",
            str(signoff_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "M3b signoff rejected" in completed.stderr
    assert "M4a remains blocked" in completed.stderr


def _write_complete_signoff_package(tmp_path: Path) -> Path:
    _write_trade_calendar(tmp_path / "trade_calendar.csv")
    events_path = tmp_path / "events.jsonl"
    signoff = _valid_signoff()
    _write_jsonl(events_path, _valid_events(signoff))

    signoff_path = tmp_path / "m3b_signoff.yaml"
    signoff_path.write_text(yaml.safe_dump(signoff, sort_keys=False), encoding="utf-8")
    return signoff_path


def _valid_signoff() -> dict[str, Any]:
    trading_days = []
    for index, date in enumerate(TRADING_DATES):
        startup_seq = index * 10 + 1
        close_seq = index * 10 + 2
        trading_days.append(
            {
                "date": date,
                "run_id": "paper-202401",
                "strategy_id": "dual_ma_510300",
                "account_id": "paper",
                "startup_reconciliation_seq": startup_seq,
                "startup_reconciliation_status": "OK",
                "close_reconciliation_seq": close_seq,
                "close_reconciliation_status": "OK",
                "unresolved_difference_count": 0,
                "manual_intervention_unresolved": False,
            }
        )

    return {
        "gate": "M3b",
        "required_trading_days": 10,
        "event_journal_path": "events.jsonl",
        "trade_calendar_path": "trade_calendar.csv",
        "counted_window": {
            "start_date": TRADING_DATES[0],
            "end_date": TRADING_DATES[-1],
            "trading_day_count": 10,
        },
        "trading_days": trading_days,
        "disconnect_drill": {
            "date": TRADING_DATES[3],
            "seq": 500,
            "recovery_seq": 501,
            "status": "RECOVERED",
            "reason": "network drill",
            "run_id": "paper-202401",
            "strategy_id": "dual_ma_510300",
            "account_id": "paper",
        },
        "crit_delivery_receipts": [
            {
                "delivery_id": "delivery-502",
                "event_seq": 502,
                "severity": "CRIT",
                "channel": "phone",
                "delivered_at": f"{TRADING_DATES[3]}T10:00:00+08:00",
                "run_id": "paper-202401",
                "strategy_id": "dual_ma_510300",
                "account_id": "paper",
            }
        ],
        "manual_intervention": {"unresolved": False, "notes": "none"},
        "final_signoff": {
            "approved": True,
            "operator": "paper-operator",
            "signed_at": "2024-01-15T16:00:00+08:00",
        },
    }


def _valid_events(signoff: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for day in signoff["trading_days"]:
        context = _context(day)
        events.append(
            _event(
                day["startup_reconciliation_seq"],
                "reconciliation",
                f"{day['date']}T09:15:00+08:00",
                context | {"startup": True, "status": day["startup_reconciliation_status"]},
            )
        )
        events.append(
            _event(
                day["close_reconciliation_seq"],
                "reconciliation",
                f"{day['date']}T15:05:00+08:00",
                context | {"startup": False, "status": day["close_reconciliation_status"]},
            )
        )

    drill = signoff["disconnect_drill"]
    events.append(
        _event(
            drill["seq"],
            "gateway_disconnect",
            f"{drill['date']}T10:00:00+08:00",
            _context(drill) | {"state": "FREEZE_OPEN", "reason": drill["reason"]},
        )
    )
    events.append(
        _event(
            drill["recovery_seq"],
            "recovery",
            f"{drill['date']}T10:10:00+08:00",
            _context(drill)
            | {"state": "NORMAL", "reason": "gateway_reconnected_reconciliation_ok"},
        )
    )

    receipt = signoff["crit_delivery_receipts"][0]
    events.append(
        _event(
            receipt["event_seq"],
            "alert",
            receipt["delivered_at"],
            _context(receipt)
            | {"severity": receipt["severity"], "delivery_id": receipt["delivery_id"]},
        )
    )
    return events


def _context(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "strategy_id": row["strategy_id"],
        "account_id": row["account_id"],
    }


def _event(
    seq: Any,
    event_type: str,
    written_at: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "seq": seq,
        "type": event_type,
        "written_at": written_at,
        "payload": payload,
    }


def _write_trade_calendar(path: Path) -> None:
    rows = ["exchange,date,is_open"]
    rows.extend(f"SH,{date},true" for date in TRADING_DATES)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )
