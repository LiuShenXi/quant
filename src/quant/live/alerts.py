from __future__ import annotations

from datetime import datetime, timedelta
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

    def __init__(self, journal: EventJournal, dedupe_sec: int) -> None:
        self.journal = journal
        self.dedupe = timedelta(seconds=dedupe_sec)
        self.last_emit: dict[str, datetime] = {}
        self.timezone = ZoneInfo("Asia/Shanghai")

    def emit(
        self,
        severity: AlertSeverity,
        key: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        if severity == AlertSeverity.CRIT:
            missing = [field for field in self.CRIT_REQUIRED_FIELDS if field not in payload]
            if missing:
                raise ValueError(f"CRIT alert missing fields: {', '.join(missing)}")

        now = datetime.now(self.timezone)
        if key in self.last_emit and now - self.last_emit[key] < self.dedupe:
            return False
        self.last_emit[key] = now

        envelope: dict[str, object] = {
            "severity": severity.value,
            "key": key,
            "message": message,
            "payload": payload,
        }
        if severity == AlertSeverity.CRIT:
            for field in self.CRIT_REQUIRED_FIELDS:
                envelope[field] = payload.get(field)

        self.journal.append("alert", envelope)
        return True
