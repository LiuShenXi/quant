from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketCalendar:
    name: str
    timezone: ZoneInfo
    continuous: bool
    session_dates: frozenset[date] | None = None
    session_close: time = time(0, 0)
    daily_boundary: time = time(0, 0)

    @classmethod
    def continuous_24x7(
        cls,
        *,
        timezone: str = "UTC",
        daily_boundary: time = time(0, 0),
    ) -> "MarketCalendar":
        return cls(
            name="continuous_24x7",
            timezone=ZoneInfo(timezone),
            continuous=True,
            daily_boundary=daily_boundary,
        )

    @classmethod
    def from_sessions(
        cls,
        *,
        name: str,
        dates: Iterable[date | str],
        timezone: str,
        session_close: time,
    ) -> "MarketCalendar":
        return cls(
            name=name,
            timezone=ZoneInfo(timezone),
            continuous=False,
            session_dates=frozenset(_coerce_date(value) for value in dates),
            session_close=session_close,
        )

    def expected_timestamps(self, start: datetime, end: datetime, freq: str) -> list[datetime]:
        local_start = _to_timezone(start, self.timezone)
        local_end = _to_timezone(end, self.timezone)
        if local_end < local_start:
            return []
        if self.continuous:
            return self._continuous_timestamps(local_start, local_end, freq)
        return self._session_timestamps(local_start, local_end, freq)

    def _continuous_timestamps(
        self,
        start: datetime,
        end: datetime,
        freq: str,
    ) -> list[datetime]:
        interval = _parse_frequency(freq)
        current = _ceil_to_interval(
            start=start,
            interval=interval,
            anchor=datetime.combine(start.date(), self.daily_boundary, tzinfo=self.timezone),
        )
        timestamps: list[datetime] = []
        while current <= end:
            timestamps.append(current)
            current += interval
        return timestamps

    def _session_timestamps(
        self,
        start: datetime,
        end: datetime,
        freq: str,
    ) -> list[datetime]:
        interval = _parse_frequency(freq)
        if interval != timedelta(days=1):
            raise ValueError(f"session calendar {self.name!r} only supports daily timestamps")
        if self.session_dates is None:
            return []
        timestamps: list[datetime] = []
        for session_date in sorted(self.session_dates):
            timestamp = datetime.combine(session_date, self.session_close, tzinfo=self.timezone)
            if start <= timestamp <= end:
                timestamps.append(timestamp)
        return timestamps


def _parse_frequency(freq: str) -> timedelta:
    normalized = freq.strip().lower()
    if normalized.endswith("h"):
        value = int(normalized[:-1])
        return timedelta(hours=value)
    if normalized.endswith("d"):
        value = int(normalized[:-1])
        return timedelta(days=value)
    raise ValueError(f"unsupported frequency {freq!r}")


def _ceil_to_interval(start: datetime, interval: timedelta, anchor: datetime) -> datetime:
    current = anchor
    while current > start:
        current -= interval
    while current < start:
        current += interval
    return current


def _coerce_date(value: date | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _to_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)
