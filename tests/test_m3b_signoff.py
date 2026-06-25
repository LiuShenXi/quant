from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from quant.live.signoff import SignoffValidationError, validate_m3b_signoff


def test_m3b_signoff_validator_accepts_complete_ten_day_evidence(tmp_path) -> None:
    signoff_path = tmp_path / "m3b_signoff.yaml"
    _write_signoff(signoff_path, _valid_signoff())

    validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_missing_daily_evidence(tmp_path) -> None:
    signoff = _valid_signoff()
    signoff["trading_days"] = signoff["trading_days"][:9]
    signoff_path = tmp_path / "m3b_signoff.yaml"
    _write_signoff(signoff_path, signoff)

    with pytest.raises(SignoffValidationError, match="exactly 10 trading days"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_incomplete_drill_or_delivery(tmp_path) -> None:
    signoff = _valid_signoff()
    signoff["disconnect_drill"]["seq"] = None
    signoff["crit_delivery_receipts"] = []
    signoff_path = tmp_path / "m3b_signoff.yaml"
    _write_signoff(signoff_path, signoff)

    with pytest.raises(SignoffValidationError, match="disconnect_drill.seq"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_template_documents_required_fields() -> None:
    template = Path("docs/runbooks/m3b_signoff_template.yaml").read_text(encoding="utf-8")
    required = [
        "required_trading_days: 10",
        "startup_reconciliation_seq",
        "close_reconciliation_seq",
        "disconnect_drill",
        "crit_delivery_receipts",
        "manual_intervention",
        "final_signoff",
    ]
    for phrase in required:
        assert phrase in template


def _write_signoff(path: Path, payload: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _valid_signoff() -> dict[str, object]:
    return {
        "gate": "M3b",
        "required_trading_days": 10,
        "trading_days": [
            {
                "date": f"2026-06-{day:02d}",
                "startup_reconciliation_seq": day * 10 + 1,
                "startup_reconciliation_status": "OK",
                "close_reconciliation_seq": day * 10 + 2,
                "close_reconciliation_status": "OK",
                "unresolved_difference_count": 0,
                "manual_intervention_unresolved": False,
            }
            for day in range(1, 11)
        ],
        "disconnect_drill": {
            "seq": 120,
            "recovery_seq": 121,
            "status": "RECOVERED",
        },
        "crit_delivery_receipts": [
            {
                "delivery_id": "delivery-1",
                "event_seq": 119,
                "channel": "dry-run-file",
                "delivered_at": "2026-06-01T09:31:00+08:00",
            }
        ],
        "manual_intervention": {
            "unresolved": False,
            "notes": "none",
        },
        "final_signoff": {
            "approved": True,
            "operator": "paper-operator",
            "signed_at": "2026-06-15T16:00:00+08:00",
        },
    }
