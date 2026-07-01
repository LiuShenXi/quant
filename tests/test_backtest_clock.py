from datetime import datetime
from zoneinfo import ZoneInfo

from quant.backtest.clock import BacktestClock
from quant.core.contract import Bar


UTC = ZoneInfo("UTC")


def test_primary_timeline_is_sorted_unique_and_timezone_aware_for_4h_bars() -> None:
    clock = BacktestClock(
        bars_by_frequency={
            "4h": [
                _bar("BBB-USD", "4h", datetime(2026, 1, 2, 4, tzinfo=UTC)),
                _bar("AAA-USD", "4h", datetime(2026, 1, 2, 0, tzinfo=UTC)),
                _bar("AAA-USD", "4h", datetime(2026, 1, 2, 4, tzinfo=UTC)),
                _bar("AAA-USD", "4h", datetime(2026, 1, 2, 8, tzinfo=UTC)),
            ],
        },
        primary_frequency="4h",
    )

    timeline = clock.primary_timeline()

    assert timeline == [
        datetime(2026, 1, 2, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 4, tzinfo=UTC),
        datetime(2026, 1, 2, 8, tzinfo=UTC),
    ]
    assert all(value.tzinfo is not None and value.utcoffset() is not None for value in timeline)


def test_visible_daily_bar_at_4h_decision_is_last_fully_closed_daily_bar() -> None:
    clock = BacktestClock(
        bars_by_frequency={
            "4h": [
                _bar("AAA-USD", "4h", datetime(2026, 1, 2, 0, tzinfo=UTC)),
                _bar("AAA-USD", "4h", datetime(2026, 1, 2, 4, tzinfo=UTC)),
            ],
            "1d": [
                _bar("AAA-USD", "1d", datetime(2026, 1, 1, 0, tzinfo=UTC)),
                _bar("AAA-USD", "1d", datetime(2026, 1, 2, 0, tzinfo=UTC)),
                _bar("AAA-USD", "1d", datetime(2026, 1, 3, 0, tzinfo=UTC)),
            ],
        },
        primary_frequency="4h",
    )

    visible = clock.visible_bar_time("1d", datetime(2026, 1, 2, 4, tzinfo=UTC))

    assert visible == datetime(2026, 1, 2, 0, tzinfo=UTC)
    assert visible != datetime(2026, 1, 3, 0, tzinfo=UTC)


def _bar(symbol: str, freq: str, dt: datetime) -> Bar:
    return Bar(
        symbol=symbol,
        freq=freq,
        dt=dt,
        open=100,
        high=101,
        low=99,
        close=100,
        volume=1_000,
        amount=100_000,
    )
