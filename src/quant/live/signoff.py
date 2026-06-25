from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SignoffValidationError(ValueError):
    pass


def validate_m3b_signoff(path: Path) -> None:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = _validate_payload(payload)
    if errors:
        raise SignoffValidationError("; ".join(errors))


def _validate_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["signoff must be a mapping"]

    errors: list[str] = []
    if payload.get("gate") != "M3b":
        errors.append("gate must be M3b")
    if payload.get("required_trading_days") != 10:
        errors.append("required_trading_days must be 10")

    trading_days = payload.get("trading_days")
    if not isinstance(trading_days, list) or len(trading_days) != 10:
        errors.append("trading_days must contain exactly 10 trading days")
    else:
        errors.extend(_validate_trading_days(trading_days))

    disconnect_drill = payload.get("disconnect_drill")
    if not isinstance(disconnect_drill, dict):
        errors.append("disconnect_drill must be present")
    else:
        if not _positive_int(disconnect_drill.get("seq")):
            errors.append("disconnect_drill.seq must be a positive integer")
        if not _positive_int(disconnect_drill.get("recovery_seq")):
            errors.append("disconnect_drill.recovery_seq must be a positive integer")
        if disconnect_drill.get("status") not in {"RECOVERED", "RECOVERY_BLOCKED"}:
            errors.append("disconnect_drill.status must be RECOVERED or RECOVERY_BLOCKED")

    receipts = payload.get("crit_delivery_receipts")
    if not isinstance(receipts, list) or not receipts:
        errors.append("crit_delivery_receipts must contain at least one receipt")
    else:
        errors.extend(_validate_receipts(receipts))

    manual_intervention = payload.get("manual_intervention")
    if not isinstance(manual_intervention, dict):
        errors.append("manual_intervention must be present")
    elif manual_intervention.get("unresolved") is not False:
        errors.append("manual_intervention.unresolved must be false")

    final_signoff = payload.get("final_signoff")
    if not isinstance(final_signoff, dict):
        errors.append("final_signoff must be present")
    else:
        if final_signoff.get("approved") is not True:
            errors.append("final_signoff.approved must be true")
        for field in ("operator", "signed_at"):
            if not _non_empty_string(final_signoff.get(field)):
                errors.append(f"final_signoff.{field} must be present")

    return errors


def _validate_trading_days(trading_days: list[Any]) -> list[str]:
    errors: list[str] = []
    seen_dates: set[str] = set()
    for index, day in enumerate(trading_days, start=1):
        prefix = f"trading_days[{index}]"
        if not isinstance(day, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        date_value = day.get("date")
        if not _non_empty_string(date_value):
            errors.append(f"{prefix}.date must be present")
        elif date_value in seen_dates:
            errors.append(f"{prefix}.date must be unique")
        else:
            seen_dates.add(date_value)
        for field in ("startup_reconciliation_seq", "close_reconciliation_seq"):
            if not _positive_int(day.get(field)):
                errors.append(f"{prefix}.{field} must be a positive integer")
        for field in ("startup_reconciliation_status", "close_reconciliation_status"):
            if day.get(field) not in {"OK", "REPAIRED"}:
                errors.append(f"{prefix}.{field} must be OK or REPAIRED")
        if day.get("unresolved_difference_count") != 0:
            errors.append(f"{prefix}.unresolved_difference_count must be 0")
        if day.get("manual_intervention_unresolved") is not False:
            errors.append(f"{prefix}.manual_intervention_unresolved must be false")
    return errors


def _validate_receipts(receipts: list[Any]) -> list[str]:
    errors: list[str] = []
    for index, receipt in enumerate(receipts, start=1):
        prefix = f"crit_delivery_receipts[{index}]"
        if not isinstance(receipt, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for field in ("delivery_id", "channel", "delivered_at"):
            if not _non_empty_string(receipt.get(field)):
                errors.append(f"{prefix}.{field} must be present")
        if not _positive_int(receipt.get("event_seq")):
            errors.append(f"{prefix}.event_seq must be a positive integer")
    return errors


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
