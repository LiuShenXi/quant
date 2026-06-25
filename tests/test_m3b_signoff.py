from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import yaml

from quant.core.contract import Account
from quant.live.alerts import AlertManager
from quant.live.events import EventJournal
from quant.live.monitor import RuntimeMonitor
from quant.live.reconcile import Reconciler
from quant.live.signoff import SignoffValidationError, validate_m3b_signoff
from quant.live.store import OmsStore

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
    "2024-01-16",
]
RUN_ID = "paper-202401"
STRATEGY_ID = "dual_ma_510300"
ACCOUNT_ID = "paper"


def test_m3b_signoff_validator_accepts_complete_evidence_with_extra_observation_days(
    tmp_path,
) -> None:
    signoff_path = _write_valid_evidence(tmp_path)

    validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_accepts_real_paper_producer_journal_schema(
    tmp_path,
) -> None:
    signoff_path = _write_real_producer_evidence(tmp_path)

    validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_missing_journal_and_calendar_paths(
    tmp_path,
) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff.pop("event_journal_path")
        signoff.pop("trade_calendar_path")

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="event_journal_path must be present"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_non_trading_dates(tmp_path) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][2]["date"] = "2024-01-06"

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="not in trade calendar"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_out_of_order_dates(tmp_path) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][0], signoff["trading_days"][1] = (
            signoff["trading_days"][1],
            signoff["trading_days"][0],
        )

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="strictly increasing"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_invalid_counted_window(tmp_path) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["counted_window"]["end_date"] = TRADING_DATES[8]
        signoff["counted_window"]["trading_day_count"] = 9

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="at least 10 counted trading days"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_duplicated_event_seq_references(
    tmp_path,
) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][0]["close_reconciliation_seq"] = signoff["trading_days"][0][
            "startup_reconciliation_seq"
        ]

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="event seq 1 is referenced more than once"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_missing_referenced_event_seq(tmp_path) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][0]["startup_reconciliation_seq"] = 9999

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="missing event seq 9999"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_wrong_event_type(tmp_path) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 1)["type"] = "order"

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match="expected type reconciliation"):
        validate_m3b_signoff(signoff_path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("status", "FAILED", "payload.status"),
        ("startup", False, "payload.startup"),
    ],
)
def test_m3b_signoff_validator_rejects_wrong_reconciliation_semantics(
    tmp_path,
    field: str,
    value: object,
    match: str,
) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 1)["payload"][field] = value

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match=match):
        validate_m3b_signoff(signoff_path)


@pytest.mark.parametrize("field", ["account_id", "strategy_id", "run_id"])
def test_m3b_signoff_validator_rejects_wrong_context_fields(
    tmp_path,
    field: str,
) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 1)["payload"][field] = f"wrong-{field}"

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match=field):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_requires_disconnect_drill_recovered_status(
    tmp_path,
) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["disconnect_drill"]["status"] = "RECOVERY_BLOCKED"

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(SignoffValidationError, match="disconnect_drill.status must be RECOVERED"):
        validate_m3b_signoff(signoff_path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("state", "FREEZE_OPEN", "payload.state"),
        ("reason", "manual_resume", "payload.reason"),
    ],
)
def test_m3b_signoff_validator_rejects_recovery_event_without_safe_recovery_semantics(
    tmp_path,
    field: str,
    value: str,
    match: str,
) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 501)["payload"][field] = value

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match=match):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_close_reconciliation_before_startup(
    tmp_path,
) -> None:
    def mutate_signoff(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][0]["startup_reconciliation_seq"] = 20
        signoff["trading_days"][0]["close_reconciliation_seq"] = 19

    def mutate_events(events: list[dict[str, Any]]) -> None:
        day = _valid_signoff()["trading_days"][0]
        events.extend(
            [
                _event(
                    20,
                    "reconciliation",
                    f"{day['date']}T09:15:00+08:00",
                    _context(day)
                    | {
                        "startup": True,
                        "status": day["startup_reconciliation_status"],
                    },
                ),
                _event(
                    19,
                    "reconciliation",
                    f"{day['date']}T15:05:00+08:00",
                    _context(day)
                    | {
                        "startup": False,
                        "status": day["close_reconciliation_status"],
                    },
                ),
            ]
        )

    signoff_path = _write_valid_evidence(
        tmp_path,
        mutate_signoff=mutate_signoff,
        mutate_events=mutate_events,
    )

    with pytest.raises(
        SignoffValidationError,
        match="close_reconciliation_seq must be after startup_reconciliation_seq",
    ):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_reconciliation_seq_regression_across_days(
    tmp_path,
) -> None:
    def mutate_signoff(signoff: dict[str, Any]) -> None:
        signoff["trading_days"][0]["close_reconciliation_seq"] = 100
        signoff["trading_days"][1]["startup_reconciliation_seq"] = 99

    def mutate_events(events: list[dict[str, Any]]) -> None:
        first_day = _valid_signoff()["trading_days"][0]
        second_day = _valid_signoff()["trading_days"][1]
        events.extend(
            [
                _event(
                    100,
                    "reconciliation",
                    f"{first_day['date']}T15:05:00+08:00",
                    _context(first_day)
                    | {
                        "startup": False,
                        "status": first_day["close_reconciliation_status"],
                    },
                ),
                _event(
                    99,
                    "reconciliation",
                    f"{second_day['date']}T09:15:00+08:00",
                    _context(second_day)
                    | {
                        "startup": True,
                        "status": second_day["startup_reconciliation_status"],
                    },
                ),
            ]
        )

    signoff_path = _write_valid_evidence(
        tmp_path,
        mutate_signoff=mutate_signoff,
        mutate_events=mutate_events,
    )

    with pytest.raises(
        SignoffValidationError,
        match="reconciliation seq values must be strictly increasing",
    ):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_malformed_iso_event_timestamp(
    tmp_path,
) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 1)["written_at"] = "2024-01-02Tnot-a-time"

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match="written_at must be a valid ISO timestamp"):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_validator_rejects_malformed_crit_delivery_timestamp(
    tmp_path,
) -> None:
    def mutate(signoff: dict[str, Any]) -> None:
        signoff["crit_delivery_receipts"][0]["delivered_at"] = "not-an-iso-timestamp"
        signoff["crit_delivery_receipts"][0]["event_seq"] = 9999

    signoff_path = _write_valid_evidence(tmp_path, mutate_signoff=mutate)

    with pytest.raises(
        SignoffValidationError,
        match="crit_delivery_receipts\\[1\\]\\.delivered_at must be a valid ISO timestamp",
    ):
        validate_m3b_signoff(signoff_path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("severity", "WARN", "payload.severity"),
        ("delivery_id", "delivery-wrong", "payload.delivery_id"),
    ],
)
def test_m3b_signoff_validator_rejects_wrong_crit_delivery_semantics(
    tmp_path,
    field: str,
    value: object,
    match: str,
) -> None:
    def mutate(events: list[dict[str, Any]]) -> None:
        _event_by_seq(events, 502)["payload"][field] = value

    signoff_path = _write_valid_evidence(tmp_path, mutate_events=mutate)

    with pytest.raises(SignoffValidationError, match=match):
        validate_m3b_signoff(signoff_path)


def test_m3b_signoff_template_documents_required_fields() -> None:
    template = Path("docs/runbooks/m3b_signoff_template.yaml").read_text(encoding="utf-8")
    required = [
        "event_journal_path",
        "trade_calendar_path",
        "counted_window",
        "required_trading_days: 10",
        "account_id",
        "strategy_id",
        "run_id",
        "startup_reconciliation_seq",
        "close_reconciliation_seq",
        "disconnect_drill",
        "crit_delivery_receipts",
        "manual_intervention",
        "final_signoff",
    ]
    for phrase in required:
        assert phrase in template


def test_live_local_config_paths_are_gitignored() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "config/live/local/" in gitignore


def test_live_config_examples_document_placeholder_only_policy() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Live config examples may contain placeholders only" in readme
    assert "config/live/local/" in readme


class GatewayForSignoff:
    def __init__(self, account: Account) -> None:
        self.account = account

    def query_account(self) -> Account:
        return self.account

    def query_positions(self) -> dict[str, object]:
        return {}

    def query_orders(self, active_only: bool = True) -> list[object]:
        return []


def _write_real_producer_evidence(tmp_path: Path) -> Path:
    journal_path = tmp_path / "events.jsonl"
    current_time = datetime(2024, 1, 2, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    def clock() -> datetime:
        return current_time

    def set_clock(date: str, hour: int, minute: int) -> None:
        nonlocal current_time
        year, month, day = (int(part) for part in date.split("-"))
        current_time = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Asia/Shanghai"))

    account = Account(ACCOUNT_ID, "CNY", 100_000, 0, 0, 100_000)
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    store.save_account_snapshot(account, {}, current_time)
    journal = EventJournal(journal_path, clock=clock)
    reconciler = Reconciler(
        store=store,
        gateway=GatewayForSignoff(account),
        journal=journal,
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
        run_id=RUN_ID,
        strategy_id=STRATEGY_ID,
        account_id=ACCOUNT_ID,
        clock=clock,
    )
    monitor = RuntimeMonitor(
        store=store,
        journal=journal,
        alert_manager=AlertManager(
            journal,
            dedupe_sec=300,
            clock=clock,
            delivery_dir=tmp_path / "alert_delivery",
        ),
        market_data_staleness_sec=60,
        run_id=RUN_ID,
        strategy_id=STRATEGY_ID,
        account_id=ACCOUNT_ID,
        clock=clock,
    )

    signoff = _valid_signoff()
    signoff["event_journal_path"] = "events.jsonl"
    signoff["trade_calendar_path"] = "trade_calendar.csv"
    signoff["trading_days"] = []
    signoff["crit_delivery_receipts"] = []
    for index, date in enumerate(TRADING_DATES[:10]):
        set_clock(date, 9, 15)
        startup = reconciler.run(startup=True)
        startup_seq = journal.last_seq

        if index == 3:
            set_clock(date, 10, 0)
            disconnect_seq = journal.last_seq + 1
            monitor.on_gateway_disconnect("network drill")
            alert_seq = disconnect_seq + 2

            set_clock(date, 10, 5)
            reconciler.run(startup=False)
            set_clock(date, 10, 10)
            recovery_seq = journal.last_seq + 2
            monitor.on_gateway_reconnect(reconciliation_ok=True)

            signoff["disconnect_drill"] = {
                "date": date,
                "seq": disconnect_seq,
                "recovery_seq": recovery_seq,
                "status": "RECOVERED",
                "reason": "network drill",
                "run_id": RUN_ID,
                "strategy_id": STRATEGY_ID,
                "account_id": ACCOUNT_ID,
            }
            signoff["crit_delivery_receipts"] = [
                {
                    "delivery_id": f"delivery-{alert_seq}",
                    "event_seq": alert_seq,
                    "severity": "CRIT",
                    "channel": "dry-run-file",
                    "delivered_at": f"{date}T10:00:00+08:00",
                    "run_id": RUN_ID,
                    "strategy_id": STRATEGY_ID,
                    "account_id": ACCOUNT_ID,
                }
            ]

        set_clock(date, 15, 5)
        close = reconciler.run(startup=False)
        close_seq = journal.last_seq
        signoff["trading_days"].append(
            {
                "date": date,
                "run_id": RUN_ID,
                "strategy_id": STRATEGY_ID,
                "account_id": ACCOUNT_ID,
                "startup_reconciliation_seq": startup_seq,
                "startup_reconciliation_status": startup.status.value,
                "close_reconciliation_seq": close_seq,
                "close_reconciliation_status": close.status.value,
                "unresolved_difference_count": 0,
                "manual_intervention_unresolved": False,
            }
        )

    _write_trade_calendar(tmp_path / "trade_calendar.csv")
    signoff_path = tmp_path / "m3b_signoff.yaml"
    signoff_path.write_text(yaml.safe_dump(signoff, sort_keys=False), encoding="utf-8")
    return signoff_path


def _write_valid_evidence(
    tmp_path: Path,
    *,
    mutate_signoff: Callable[[dict[str, Any]], None] | None = None,
    mutate_events: Callable[[list[dict[str, Any]]], None] | None = None,
) -> Path:
    signoff = _valid_signoff()
    events = _valid_events(signoff)
    if mutate_signoff is not None:
        mutate_signoff(signoff)
    if mutate_events is not None:
        mutate_events(events)

    _write_trade_calendar(tmp_path / "trade_calendar.csv")
    _write_jsonl(tmp_path / "events.jsonl", events)

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
                "run_id": RUN_ID,
                "strategy_id": STRATEGY_ID,
                "account_id": ACCOUNT_ID,
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
            "end_date": TRADING_DATES[9],
            "trading_day_count": 10,
        },
        "trading_days": trading_days,
        "disconnect_drill": {
            "date": TRADING_DATES[3],
            "seq": 500,
            "recovery_seq": 501,
            "status": "RECOVERED",
            "reason": "network drill",
            "run_id": RUN_ID,
            "strategy_id": STRATEGY_ID,
            "account_id": ACCOUNT_ID,
        },
        "crit_delivery_receipts": [
            {
                "delivery_id": "delivery-502",
                "event_seq": 502,
                "severity": "CRIT",
                "channel": "dry-run-file",
                "delivered_at": f"{TRADING_DATES[4]}T09:31:00+08:00",
                "run_id": RUN_ID,
                "strategy_id": STRATEGY_ID,
                "account_id": ACCOUNT_ID,
            }
        ],
        "manual_intervention": {
            "unresolved": False,
            "notes": "none",
        },
        "final_signoff": {
            "approved": True,
            "operator": "paper-operator",
            "signed_at": "2024-01-16T16:00:00+08:00",
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
                context
                | {
                    "startup": True,
                    "status": day["startup_reconciliation_status"],
                },
            )
        )
        events.append(
            _event(
                day["close_reconciliation_seq"],
                "reconciliation",
                f"{day['date']}T15:05:00+08:00",
                context
                | {
                    "startup": False,
                    "status": day["close_reconciliation_status"],
                },
            )
        )

    drill = signoff["disconnect_drill"]
    events.append(
        _event(
            drill["seq"],
            "gateway_disconnect",
            f"{drill['date']}T10:00:00+08:00",
            _context(drill)
            | {
                "state": "FREEZE_OPEN",
                "reason": drill["reason"],
            },
        )
    )
    events.append(
        _event(
            drill["recovery_seq"],
            "recovery",
            f"{drill['date']}T10:10:00+08:00",
            _context(drill)
            | {
                "state": "NORMAL",
                "reason": "gateway_reconnected_reconciliation_ok",
            },
        )
    )

    receipt = signoff["crit_delivery_receipts"][0]
    events.append(
        _event(
            receipt["event_seq"],
            "alert",
            receipt["delivered_at"],
            _context(receipt)
            | {
                "severity": receipt["severity"],
                "delivery_id": receipt["delivery_id"],
                "key": "gateway_disconnect",
            },
        )
    )
    return events


def _context(row: dict[str, Any]) -> dict[str, str]:
    return {
        "run_id": row["run_id"],
        "strategy_id": row["strategy_id"],
        "account_id": row["account_id"],
    }


def _event(seq: int, event_type: str, written_at: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "seq": seq,
        "type": event_type,
        "written_at": written_at,
        "payload": payload,
    }


def _event_by_seq(events: list[dict[str, Any]], seq: int) -> dict[str, Any]:
    for event in events:
        if event["seq"] == seq:
            return event
    raise AssertionError(f"missing test event seq {seq}")


def _write_trade_calendar(path: Path) -> None:
    rows = ["exchange,date,is_open"]
    rows.extend(f"SH,{date},true" for date in TRADING_DATES)
    rows.append("SH,2024-01-06,false")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    cloned = [deepcopy(event) for event in events]
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in cloned) + "\n",
        encoding="utf-8",
    )
