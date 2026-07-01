from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class JournalEvent:
    run_id: str
    seq: int
    event_type: str
    timestamp: datetime
    source_component: str
    strategy_id: str | None = None
    account_id: str | None = None
    symbol: str | None = None
    order_id: str | None = None
    trade_id: str | None = None
    risk_rule_id: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class EventJournal:
    _ID_FIELDS = {
        "strategy_id",
        "account_id",
        "symbol",
        "order_id",
        "trade_id",
        "risk_rule_id",
        "correlation_id",
    }

    def __init__(self, run_id: str) -> None:
        if not run_id.strip():
            raise ValueError("run_id must not be empty")
        self.run_id = run_id
        self._seq = 0
        self._events: list[JournalEvent] = []

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        event_type: str,
        timestamp: datetime,
        source_component: str,
        payload: dict[str, Any],
        **ids: str | None,
    ) -> JournalEvent:
        unknown_ids = set(ids) - self._ID_FIELDS
        if unknown_ids:
            names = ", ".join(sorted(unknown_ids))
            raise TypeError(f"unknown journal id field(s): {names}")
        self._seq += 1
        event = JournalEvent(
            run_id=self.run_id,
            seq=self._seq,
            event_type=event_type,
            timestamp=timestamp,
            source_component=source_component,
            strategy_id=ids.get("strategy_id"),
            account_id=ids.get("account_id"),
            symbol=ids.get("symbol"),
            order_id=ids.get("order_id"),
            trade_id=ids.get("trade_id"),
            risk_rule_id=ids.get("risk_rule_id"),
            correlation_id=ids.get("correlation_id"),
            payload=dict(payload),
        )
        self._events.append(event)
        return event
