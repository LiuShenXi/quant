from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from quant.data.calendar import MarketCalendar


UTC = ZoneInfo("UTC")


def test_continuous_24x7_generates_utc_aware_4h_timestamps_across_weekend() -> None:
    calendar = MarketCalendar.continuous_24x7(timezone="UTC")

    timestamps = calendar.expected_timestamps(
        start=datetime(2024, 1, 5, 20, 0, tzinfo=UTC),
        end=datetime(2024, 1, 7, 4, 0, tzinfo=UTC),
        freq="4h",
    )

    assert timestamps == [
        datetime(2024, 1, 5, 20, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 4, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 8, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 12, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 16, 0, tzinfo=UTC),
        datetime(2024, 1, 6, 20, 0, tzinfo=UTC),
        datetime(2024, 1, 7, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 7, 4, 0, tzinfo=UTC),
    ]
    assert all(timestamp.tzinfo is not None for timestamp in timestamps)


def test_continuous_daily_boundary_defaults_to_utc_midnight() -> None:
    calendar = MarketCalendar.continuous_24x7(timezone="UTC")

    timestamps = calendar.expected_timestamps(
        start=datetime(2024, 1, 1, 3, 0, tzinfo=UTC),
        end=datetime(2024, 1, 3, 1, 0, tzinfo=UTC),
        freq="1d",
    )

    assert timestamps == [
        datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 3, 0, 0, tzinfo=UTC),
    ]


def test_session_calendar_can_represent_one_event_per_legacy_daily_bar() -> None:
    data_root = Path("data_sample")
    trade_calendar = pd.read_csv(data_root / "trade_calendar.csv")
    bars = pd.read_csv(data_root / "bars_1d.csv", parse_dates=["dt"])
    expected_bar_times = [
        value.to_pydatetime()
        for value in bars[bars["symbol"] == "510300.SH"].sort_values("dt")["dt"]
    ]
    open_dates = trade_calendar[
        (trade_calendar["exchange"] == "SH") & (trade_calendar["is_open"])
    ]["date"]
    calendar = MarketCalendar.from_sessions(
        name="data_sample_sh_daily",
        dates=open_dates,
        timezone="Asia/Shanghai",
        session_close=time(15, 0),
    )

    timestamps = calendar.expected_timestamps(
        start=expected_bar_times[0],
        end=expected_bar_times[-1],
        freq="1d",
    )

    assert timestamps == expected_bar_times
