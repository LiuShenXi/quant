from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from quant.core.contract import Bar


@dataclass(frozen=True)
class FrequencyState:
    freq: str
    bars: tuple[Bar, ...]
    timeline: tuple[datetime, ...]

    @classmethod
    def from_bars(cls, freq: str, bars: Sequence[Bar]) -> "FrequencyState":
        sorted_bars = tuple(sorted(bars, key=lambda bar: (bar.dt, bar.symbol)))
        timeline = tuple(sorted({bar.dt for bar in sorted_bars}))
        return cls(freq=freq, bars=sorted_bars, timeline=timeline)

    def visible_bar_time(self, decision_time: datetime) -> datetime | None:
        index = bisect_right(self.timeline, decision_time) - 1
        if index < 0:
            return None
        return self.timeline[index]


class BacktestClock:
    def __init__(
        self,
        *,
        bars_by_frequency: Mapping[str, Sequence[Bar]],
        primary_frequency: str,
    ) -> None:
        self.primary_frequency = primary_frequency
        self._states = {
            freq: FrequencyState.from_bars(freq, bars)
            for freq, bars in bars_by_frequency.items()
        }
        if primary_frequency not in self._states:
            raise ValueError(f"primary frequency {primary_frequency!r} has no loaded bars")

    def primary_timeline(self) -> list[datetime]:
        return list(self._states[self.primary_frequency].timeline)

    def visible_bar_time(self, freq: str, decision_time: datetime) -> datetime | None:
        state = self._states.get(freq)
        if state is None:
            return None
        return state.visible_bar_time(decision_time)
