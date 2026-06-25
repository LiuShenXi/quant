from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from quant.live.events import EventJournal
from quant.live.types import AlertSeverity


class AlertManager:
    CRIT_REQUIRED_FIELDS = (
        "run_id",
        "strategy_id",
        "account_id",
        "last_event_seq",
        "local_time",
        "market_time",
    )

    def __init__(
        self,
        journal: EventJournal,
        dedupe_sec: int,
        *,
        clock: Callable[[], datetime] | None = None,
        delivery_dir: Path | None = None,
    ) -> None:
        self.journal = journal
        self.dedupe = timedelta(seconds=dedupe_sec)
        self.last_emit: dict[tuple[object, ...], datetime] = {}
        self.timezone = ZoneInfo("Asia/Shanghai")
        self.clock = clock or (lambda: datetime.now(self.timezone))
        self.delivery_dir = delivery_dir

    def emit(
        self,
        severity: AlertSeverity,
        key: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        if severity == AlertSeverity.CRIT:
            missing = [
                field
                for field in self.CRIT_REQUIRED_FIELDS
                if field not in payload or not _is_usable_crit_value(payload[field])
            ]
            if missing:
                raise ValueError(f"CRIT alert missing fields: {', '.join(missing)}")

        now = self.clock()
        dedupe_key = _dedupe_key(key, payload)
        if dedupe_key in self.last_emit and now - self.last_emit[dedupe_key] < self.dedupe:
            self.journal.append(
                "alert_suppressed",
                {
                    "severity": severity.value,
                    "key": key,
                    "message": message,
                    "payload": payload,
                },
            )
            return False
        self.last_emit[dedupe_key] = now

        delivery_id = f"delivery-{self.journal.last_seq + 1}"
        envelope: dict[str, object] = {
            "severity": severity.value,
            "key": key,
            "message": message,
            "payload": payload,
        }
        if severity == AlertSeverity.CRIT:
            for field in self.CRIT_REQUIRED_FIELDS:
                envelope[field] = payload.get(field)
            envelope["delivery_id"] = delivery_id

        event_seq = self.journal.append("alert", envelope)
        if severity == AlertSeverity.CRIT and self.delivery_dir is not None:
            self._write_delivery_receipt(delivery_id, event_seq, key, message, payload, now)
        return True

    def _write_delivery_receipt(
        self,
        delivery_id: str,
        event_seq: int,
        key: str,
        message: str,
        payload: dict[str, object],
        now: datetime,
    ) -> None:
        if self.delivery_dir is None:
            return
        self.delivery_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "delivery_id": delivery_id,
            "event_seq": event_seq,
            "channel": "dry-run-file",
            "key": key,
            "message": message,
            "payload": payload,
            "delivered_at": now.isoformat(),
        }
        (self.delivery_dir / f"{delivery_id}.json").write_text(
            json.dumps(receipt, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


def _is_usable_crit_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _dedupe_key(key: str, payload: dict[str, object]) -> tuple[object, ...]:
    return (
        payload.get("run_id"),
        payload.get("account_id"),
        payload.get("strategy_id"),
        key,
        payload.get("reason"),
    )
