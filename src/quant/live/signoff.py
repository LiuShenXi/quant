from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class SignoffValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EventExpectation:
    label: str
    seq: int
    event_type: str
    event_date: str
    payload: dict[str, object]


def validate_m3b_signoff(path: Path) -> None:
    path = Path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = _validate_payload(payload, base_dir=path.parent)
    if errors:
        raise SignoffValidationError("; ".join(errors))


def _validate_payload(payload: Any, *, base_dir: Path) -> list[str]:
    if not isinstance(payload, dict):
        return ["signoff must be a mapping"]

    errors: list[str] = []
    if payload.get("gate") != "M3b":
        errors.append("gate must be M3b")
    if payload.get("required_trading_days") != 10:
        errors.append("required_trading_days must be 10")
    required_trading_days = payload.get("required_trading_days")
    if not _positive_int(required_trading_days):
        required_trading_days = 10

    trade_calendar = _load_referenced_trade_calendar(payload, base_dir, errors)
    journal_events = _load_referenced_event_journal(payload, base_dir, errors)

    trading_days = payload.get("trading_days")
    if not isinstance(trading_days, list) or len(trading_days) < required_trading_days:
        errors.append(
            f"trading_days must contain at least {required_trading_days} trading days"
        )
    else:
        errors.extend(_validate_trading_days(trading_days, trade_calendar))
        errors.extend(
            _validate_counted_window(
                payload.get("counted_window"),
                trading_days,
                trade_calendar,
                required_trading_days,
            )
        )

    disconnect_drill = payload.get("disconnect_drill")
    if not isinstance(disconnect_drill, dict):
        errors.append("disconnect_drill must be present")
    else:
        errors.extend(_validate_disconnect_drill(disconnect_drill))

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

    if isinstance(trading_days, list) and isinstance(disconnect_drill, dict) and isinstance(
        receipts,
        list,
    ):
        errors.extend(
            _validate_event_references(
                trading_days,
                disconnect_drill,
                receipts,
                journal_events,
            )
        )

    return errors


def _load_referenced_trade_calendar(
    payload: dict[str, Any],
    base_dir: Path,
    errors: list[str],
) -> set[str] | None:
    path = _referenced_path(payload, "trade_calendar_path", base_dir, errors)
    if path is None:
        return None
    if not path.exists():
        errors.append(f"trade_calendar_path does not exist: {path}")
        return None

    dates: set[str] = set()
    try:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                date = row.get("date")
                is_open = str(row.get("is_open", "")).strip().lower()
                if date and is_open in {"true", "1", "yes"}:
                    dates.add(date)
    except OSError as error:
        errors.append(f"trade_calendar_path could not be read: {error}")
        return None

    if not dates:
        errors.append("trade_calendar_path must contain open trading dates")
    return dates


def _load_referenced_event_journal(
    payload: dict[str, Any],
    base_dir: Path,
    errors: list[str],
) -> dict[int, dict[str, Any]] | None:
    path = _referenced_path(payload, "event_journal_path", base_dir, errors)
    if path is None:
        return None
    if not path.exists():
        errors.append(f"event_journal_path does not exist: {path}")
        return None

    events: dict[int, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        errors.append(f"event_journal_path could not be read: {error}")
        return None

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"event_journal_path line {line_number} is invalid JSON: {error}")
            continue
        if not isinstance(event, dict):
            errors.append(f"event_journal_path line {line_number} must be a mapping")
            continue
        seq = event.get("seq")
        if not _positive_int(seq):
            errors.append(f"event_journal_path line {line_number}.seq must be a positive integer")
            continue
        if seq in events:
            errors.append(f"event_journal_path contains duplicate seq {seq}")
            continue
        events[seq] = event
    return events


def _referenced_path(
    payload: dict[str, Any],
    field: str,
    base_dir: Path,
    errors: list[str],
) -> Path | None:
    value = payload.get(field)
    if not _non_empty_string(value):
        errors.append(f"{field} must be present")
        return None

    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path
    signoff_relative = base_dir / raw_path
    if signoff_relative.exists():
        return signoff_relative
    cwd_relative = Path(value)
    if cwd_relative.exists():
        return cwd_relative
    return signoff_relative


def _validate_trading_days(
    trading_days: list[Any],
    trade_calendar: set[str] | None,
) -> list[str]:
    errors: list[str] = []
    previous_date: str | None = None
    previous_reconciliation_seq: int | None = None
    for index, day in enumerate(trading_days, start=1):
        prefix = f"trading_days[{index}]"
        if not isinstance(day, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        date_value = day.get("date")
        if not _non_empty_string(date_value):
            errors.append(f"{prefix}.date must be present")
        else:
            if previous_date is not None and date_value <= previous_date:
                errors.append("trading_days dates must be strictly increasing")
            previous_date = date_value
            if trade_calendar is not None and date_value not in trade_calendar:
                errors.append(f"{prefix}.date {date_value} is not in trade calendar")
        for field in ("run_id", "strategy_id", "account_id"):
            if not _non_empty_string(day.get(field)):
                errors.append(f"{prefix}.{field} must be present")
        for field in ("startup_reconciliation_seq", "close_reconciliation_seq"):
            if not _positive_int(day.get(field)):
                errors.append(f"{prefix}.{field} must be a positive integer")
        for field in ("startup_reconciliation_status", "close_reconciliation_status"):
            if day.get(field) not in {"OK", "REPAIRED"}:
                errors.append(f"{prefix}.{field} must be OK or REPAIRED")
        startup_seq = day.get("startup_reconciliation_seq")
        close_seq = day.get("close_reconciliation_seq")
        if _positive_int(startup_seq) and _positive_int(close_seq) and close_seq <= startup_seq:
            errors.append(
                f"{prefix}.close_reconciliation_seq must be after "
                "startup_reconciliation_seq"
            )
        for seq in (startup_seq, close_seq):
            if not _positive_int(seq):
                continue
            if previous_reconciliation_seq is not None and seq <= previous_reconciliation_seq:
                errors.append("trading_days reconciliation seq values must be strictly increasing")
            previous_reconciliation_seq = seq
        if day.get("unresolved_difference_count") != 0:
            errors.append(f"{prefix}.unresolved_difference_count must be 0")
        if day.get("manual_intervention_unresolved") is not False:
            errors.append(f"{prefix}.manual_intervention_unresolved must be false")
    return errors


def _validate_counted_window(
    counted_window: Any,
    trading_days: list[Any],
    trade_calendar: set[str] | None,
    required_trading_days: int,
) -> list[str]:
    if not isinstance(counted_window, dict):
        return ["counted_window must be present"]

    errors: list[str] = []
    start_date = counted_window.get("start_date")
    end_date = counted_window.get("end_date")
    declared_count = counted_window.get("trading_day_count")
    if not _non_empty_string(start_date):
        errors.append("counted_window.start_date must be present")
    if not _non_empty_string(end_date):
        errors.append("counted_window.end_date must be present")
    if not _positive_int(declared_count):
        errors.append("counted_window.trading_day_count must be a positive integer")
    if errors:
        return errors
    if end_date < start_date:
        return ["counted_window.end_date must be on or after start_date"]

    counted_dates = []
    for day in trading_days:
        if not isinstance(day, dict):
            continue
        date_value = day.get("date")
        if not _non_empty_string(date_value) or not (start_date <= date_value <= end_date):
            continue
        if trade_calendar is not None and date_value not in trade_calendar:
            continue
        counted_dates.append(date_value)

    counted_count = len(counted_dates)
    if counted_count < required_trading_days:
        errors.append(
            f"counted_window must include at least {required_trading_days} counted trading days"
        )
    if declared_count != counted_count:
        errors.append(
            "counted_window.trading_day_count must match counted trading days "
            f"({counted_count})"
        )
    return errors


def _validate_disconnect_drill(disconnect_drill: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _non_empty_string(disconnect_drill.get("date")):
        errors.append("disconnect_drill.date must be present")
    if not _positive_int(disconnect_drill.get("seq")):
        errors.append("disconnect_drill.seq must be a positive integer")
    if not _positive_int(disconnect_drill.get("recovery_seq")):
        errors.append("disconnect_drill.recovery_seq must be a positive integer")
    if disconnect_drill.get("status") != "RECOVERED":
        errors.append("disconnect_drill.status must be RECOVERED")
    if not _non_empty_string(disconnect_drill.get("reason")):
        errors.append("disconnect_drill.reason must be present")
    for field in ("run_id", "strategy_id", "account_id"):
        if not _non_empty_string(disconnect_drill.get(field)):
            errors.append(f"disconnect_drill.{field} must be present")
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
        if receipt.get("severity") != "CRIT":
            errors.append(f"{prefix}.severity must be CRIT")
        if not _positive_int(receipt.get("event_seq")):
            errors.append(f"{prefix}.event_seq must be a positive integer")
        for field in ("run_id", "strategy_id", "account_id"):
            if not _non_empty_string(receipt.get(field)):
                errors.append(f"{prefix}.{field} must be present")
    return errors


def _validate_event_references(
    trading_days: list[Any],
    disconnect_drill: dict[str, Any],
    receipts: list[Any],
    journal_events: dict[int, dict[str, Any]] | None,
) -> list[str]:
    if journal_events is None:
        return []

    expectations = _event_expectations(trading_days, disconnect_drill, receipts)
    errors = _validate_unique_event_references(expectations)
    for expectation in expectations:
        event = journal_events.get(expectation.seq)
        if event is None:
            errors.append(f"{expectation.label}: missing event seq {expectation.seq}")
            continue
        errors.extend(_validate_event(expectation, event))
    return errors


def _event_expectations(
    trading_days: list[Any],
    disconnect_drill: dict[str, Any],
    receipts: list[Any],
) -> list[EventExpectation]:
    expectations: list[EventExpectation] = []
    for index, day in enumerate(trading_days, start=1):
        if not isinstance(day, dict) or not _non_empty_string(day.get("date")):
            continue
        context = _expected_context(day)
        if _positive_int(day.get("startup_reconciliation_seq")):
            expectations.append(
                EventExpectation(
                    label=f"trading_days[{index}].startup_reconciliation_seq",
                    seq=day["startup_reconciliation_seq"],
                    event_type="reconciliation",
                    event_date=day["date"],
                    payload=context
                    | {
                        "startup": True,
                        "status": day.get("startup_reconciliation_status"),
                    },
                )
            )
        if _positive_int(day.get("close_reconciliation_seq")):
            expectations.append(
                EventExpectation(
                    label=f"trading_days[{index}].close_reconciliation_seq",
                    seq=day["close_reconciliation_seq"],
                    event_type="reconciliation",
                    event_date=day["date"],
                    payload=context
                    | {
                        "startup": False,
                        "status": day.get("close_reconciliation_status"),
                    },
                )
            )

    if _positive_int(disconnect_drill.get("seq")) and _non_empty_string(
        disconnect_drill.get("date")
    ):
        expectations.append(
            EventExpectation(
                label="disconnect_drill.seq",
                seq=disconnect_drill["seq"],
                event_type="gateway_disconnect",
                event_date=disconnect_drill["date"],
                payload=_expected_context(disconnect_drill)
                | {
                    "reason": disconnect_drill.get("reason"),
                    "state": "FREEZE_OPEN",
                },
            )
        )
    if _positive_int(disconnect_drill.get("recovery_seq")) and _non_empty_string(
        disconnect_drill.get("date")
    ):
        expectations.append(
            EventExpectation(
                label="disconnect_drill.recovery_seq",
                seq=disconnect_drill["recovery_seq"],
                event_type="recovery",
                event_date=disconnect_drill["date"],
                payload=_expected_context(disconnect_drill)
                | {
                    "state": "NORMAL",
                    "reason": "gateway_reconnected_reconciliation_ok",
                },
            )
        )

    for index, receipt in enumerate(receipts, start=1):
        if not isinstance(receipt, dict) or not _positive_int(receipt.get("event_seq")):
            continue
        delivered_date = _date_from_iso(receipt.get("delivered_at"))
        if delivered_date is None:
            continue
        expectations.append(
            EventExpectation(
                label=f"crit_delivery_receipts[{index}].event_seq",
                seq=receipt["event_seq"],
                event_type="alert",
                event_date=delivered_date,
                payload=_expected_context(receipt)
                | {
                    "severity": receipt.get("severity"),
                    "delivery_id": receipt.get("delivery_id"),
                },
            )
        )
    return expectations


def _validate_unique_event_references(expectations: list[EventExpectation]) -> list[str]:
    errors: list[str] = []
    seen: dict[int, str] = {}
    for expectation in expectations:
        if expectation.seq in seen:
            errors.append(
                f"{expectation.label}: event seq {expectation.seq} "
                "is referenced more than once"
            )
        else:
            seen[expectation.seq] = expectation.label
    return errors


def _validate_event(
    expectation: EventExpectation,
    event: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if event.get("type") != expectation.event_type:
        errors.append(
            f"{expectation.label}: event seq {expectation.seq} expected type "
            f"{expectation.event_type}"
        )

    event_date = _date_from_iso(event.get("written_at"))
    if event_date is None:
        errors.append(
            f"{expectation.label}: event seq {expectation.seq}.written_at must be "
            "a valid ISO timestamp"
        )
    elif event_date != expectation.event_date:
        errors.append(
            f"{expectation.label}: event seq {expectation.seq} event date must be "
            f"{expectation.event_date}"
        )

    payload = event.get("payload")
    if not isinstance(payload, dict):
        errors.append(f"{expectation.label}: event seq {expectation.seq}.payload must be a mapping")
        return errors
    for field, expected_value in expectation.payload.items():
        if payload.get(field) != expected_value:
            errors.append(
                f"{expectation.label}: event seq {expectation.seq} payload.{field} "
                f"must be {expected_value!r}"
            )
    return errors


def _expected_context(row: dict[str, Any]) -> dict[str, object]:
    context: dict[str, object] = {}
    for field in ("run_id", "strategy_id", "account_id"):
        if _non_empty_string(row.get(field)):
            context[field] = row[field]
    return context


def _date_from_iso(value: Any) -> str | None:
    if not _non_empty_string(value):
        return None
    raw_value = value.strip()
    if raw_value.endswith("Z"):
        raw_value = f"{raw_value[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw_value).date().isoformat()
    except ValueError:
        return None


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
