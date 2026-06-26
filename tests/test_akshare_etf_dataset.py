from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from quant.data.akshare_etf import build_etf_dataset, fetch_etf_dataset, write_dataset
from quant.data.service import DataService


def test_build_etf_dataset_converts_akshare_frames_to_platform_schema(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {
                "日期": "2024-01-02",
                "开盘": 3.502,
                "收盘": 3.453,
                "最高": 3.502,
                "最低": 3.451,
                "成交量": 1_000,
                "成交额": 3_453_000.0,
            },
            {
                "日期": "2024-01-03",
                "开盘": 3.446,
                "收盘": 3.443,
                "最高": 3.460,
                "最低": 3.428,
                "成交量": 1_200,
                "成交额": 4_131_600.0,
            },
        ]
    )
    qfq = raw.copy()
    qfq["收盘"] = [3.40, 3.443]
    calendar = pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03", "2024-01-04"]})

    dataset = build_etf_dataset(
        raw_bars=raw,
        qfq_bars=qfq,
        trade_calendar=calendar,
        symbol="510300.SH",
        name="沪深300ETF",
        updated_at=datetime(2024, 1, 3, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        source="akshare:fund_etf_hist_em",
    )

    bars = dataset["bars_1d"]
    assert bars.columns.tolist() == [
        "symbol",
        "dt",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "pre_close",
        "limit_up",
        "limit_down",
        "suspended",
        "data_status",
        "source",
        "updated_at",
    ]
    assert bars.iloc[0]["dt"] == "2024-01-02T15:00:00+08:00"
    assert bars.iloc[0]["volume"] == 100_000
    assert bars.iloc[0]["pre_close"] == 3.453
    assert bars.iloc[1]["pre_close"] == 3.453
    assert bars.iloc[1]["limit_up"] == 3.798
    assert bars.iloc[1]["limit_down"] == 3.108
    assert set(bars["data_status"]) == {"ok"}

    instruments = dataset["instruments"]
    assert instruments.iloc[0].to_dict() == {
        "symbol": "510300.SH",
        "name": "沪深300ETF",
        "type": "etf",
        "exchange": "SH",
        "list_date": "2024-01-02",
        "delist_date": "",
        "lot_size": 100,
        "qty_step": 100,
        "tick_size": 0.001,
        "t_plus": 1,
        "status": "active",
    }

    factors = dataset["adjust_factors"]
    assert factors["symbol"].tolist() == ["510300.SH", "510300.SH"]
    assert factors["ex_date"].tolist() == ["2024-01-02", "2024-01-03"]
    assert round(float(factors.iloc[0]["factor"]), 6) == round(3.40 / 3.453, 6)
    assert float(factors.iloc[1]["factor"]) == 1.0

    trade_calendar = dataset["trade_calendar"]
    assert trade_calendar.to_dict("records") == [
        {"exchange": "SH", "date": "2024-01-02", "is_open": True},
        {"exchange": "SH", "date": "2024-01-03", "is_open": True},
        {"exchange": "SH", "date": "2024-01-04", "is_open": True},
    ]

    write_dataset(dataset, tmp_path)
    service = DataService(tmp_path)
    history = service.history(
        "510300.SH",
        end=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        n=2,
        fields=["close"],
    )
    assert round(float(history.iloc[0]["close"]), 6) == round(3.40, 6)


def test_fetch_etf_dataset_uses_akshare_client_and_limits_calendar() -> None:
    class FakeAkshare:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str, str, str]] = []

        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            self.calls.append((symbol, period, start_date, end_date, adjust))
            frame = pd.DataFrame(
                [
                    {
                        "日期": "2024-01-02",
                        "开盘": 3.50,
                        "收盘": 3.45,
                        "最高": 3.51,
                        "最低": 3.44,
                        "成交量": 10,
                        "成交额": 34_500.0,
                    }
                ]
            )
            if adjust == "qfq":
                frame["收盘"] = 3.45
            return frame

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame(
                {"trade_date": ["2023-12-29", "2024-01-02", "2024-01-03"]}
            )

    client = FakeAkshare()

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20240102",
        end_date="20240103",
        client=client,
        updated_at=datetime(2024, 1, 3, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert client.calls == [
        ("510300", "daily", "20240102", "20240103", ""),
        ("510300", "daily", "20240102", "20240103", "qfq"),
    ]
    assert dataset["bars_1d"]["symbol"].tolist() == ["510300.SH"]
    assert dataset["trade_calendar"]["date"].tolist() == ["2024-01-02", "2024-01-03"]


def test_fetch_etf_dataset_drops_same_day_bar_before_close() -> None:
    class SameDayAkshare:
        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "日期": "2026-06-25",
                        "开盘": 4.97,
                        "收盘": 5.05,
                        "最高": 5.06,
                        "最低": 4.96,
                        "成交量": 10,
                        "成交额": 50_500.0,
                    },
                    {
                        "日期": "2026-06-26",
                        "开盘": 5.01,
                        "收盘": 4.91,
                        "最高": 5.02,
                        "最低": 4.88,
                        "成交量": 3,
                        "成交额": 14_730.0,
                    },
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2026-06-25", "2026-06-26"]})

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20260625",
        end_date="20260626",
        client=SameDayAkshare(),
        updated_at=datetime(2026, 6, 26, 11, 50, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert dataset["bars_1d"]["dt"].tolist() == ["2026-06-25T15:00:00+08:00"]
    assert dataset["trade_calendar"]["date"].tolist() == ["2026-06-25"]


def test_fetch_etf_dataset_retries_transient_vendor_errors() -> None:
    class FlakyAkshare:
        def __init__(self) -> None:
            self.raw_attempts = 0

        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            if adjust == "":
                self.raw_attempts += 1
                if self.raw_attempts == 1:
                    raise ConnectionError("temporary vendor disconnect")
            return pd.DataFrame(
                [
                    {
                        "日期": "2024-01-02",
                        "开盘": 3.50,
                        "收盘": 3.45,
                        "最高": 3.51,
                        "最低": 3.44,
                        "成交量": 10,
                        "成交额": 34_500.0,
                    }
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2024-01-02"]})

    client = FlakyAkshare()

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20240102",
        end_date="20240102",
        client=client,
        updated_at=datetime(2024, 1, 2, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        retries=2,
    )

    assert client.raw_attempts == 2
    assert len(dataset["bars_1d"]) == 1


def test_fetch_etf_dataset_falls_back_to_sina_when_eastmoney_fails() -> None:
    class SinaFallbackAkshare:
        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            raise ConnectionError("eastmoney unavailable")

        def fund_etf_hist_sina(self, symbol: str) -> pd.DataFrame:
            assert symbol == "sh510300"
            return pd.DataFrame(
                [
                    {
                        "date": "2023-12-29",
                        "open": 3.40,
                        "high": 3.42,
                        "low": 3.38,
                        "close": 3.41,
                        "volume": 10_000,
                        "amount": 34_100.0,
                    },
                    {
                        "date": "2024-01-02",
                        "open": 3.50,
                        "high": 3.51,
                        "low": 3.44,
                        "close": 3.45,
                        "volume": 12_000,
                        "amount": 41_400.0,
                    },
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2024-01-02"]})

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20240101",
        end_date="20240103",
        client=SinaFallbackAkshare(),
        updated_at=datetime(2024, 1, 3, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        retries=1,
    )

    bars = dataset["bars_1d"]
    assert bars["dt"].tolist() == ["2024-01-02T15:00:00+08:00"]
    assert bars["volume"].tolist() == [12_000.0]
    assert bars["source"].tolist() == ["akshare:fund_etf_hist_sina"]
    assert dataset["adjust_factors"]["factor"].tolist() == [1.0]


def test_fetch_etf_dataset_uses_sina_dividends_for_qfq_factors(tmp_path: Path) -> None:
    class DividendAkshare:
        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            raise ConnectionError("eastmoney unavailable")

        def fund_etf_hist_sina(self, symbol: str) -> pd.DataFrame:
            assert symbol == "sh510300"
            return pd.DataFrame(
                [
                    {
                        "date": "2025-06-19",
                        "open": 3.898,
                        "high": 3.899,
                        "low": 3.863,
                        "close": 3.873,
                        "volume": 600_788_572,
                        "amount": 2_331_339_243.0,
                    },
                    {
                        "date": "2026-01-19",
                        "open": 4.001,
                        "high": 4.011,
                        "low": 3.990,
                        "close": 4.000,
                        "volume": 100_000_000,
                        "amount": 400_000_000.0,
                    },
                ]
            )

        def fund_etf_dividend_sina(self, symbol: str) -> pd.DataFrame:
            assert symbol == "sh510300"
            return pd.DataFrame(
                [
                    {"日期": "2025-06-18", "累计分红": 0.757},
                    {"日期": "2026-01-19", "累计分红": 0.880},
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2025-06-19", "2026-01-19"]})

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20250601",
        end_date="20260626",
        client=DividendAkshare(),
        updated_at=datetime(2026, 6, 26, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        retries=1,
    )

    factors = dataset["adjust_factors"]
    june_factor = float(factors[factors["ex_date"] == "2025-06-19"].iloc[0]["factor"])
    assert round(june_factor, 6) == round(3.750 / 3.873, 6)

    write_dataset(dataset, tmp_path)
    service = DataService(tmp_path)
    history = service.history(
        "510300.SH",
        end=datetime(2026, 6, 26, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        n=2,
        fields=["close"],
    )
    assert round(float(history.iloc[0]["close"]), 3) == 3.750


def test_fetch_etf_dataset_supplements_missing_same_day_sina_bar() -> None:
    class SameDaySupplementAkshare:
        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            raise ConnectionError("eastmoney unavailable")

        def fund_etf_hist_sina(self, symbol: str) -> pd.DataFrame:
            assert symbol == "sh510300"
            return pd.DataFrame(
                [
                    {
                        "date": "2026-06-25",
                        "open": 4.970,
                        "high": 5.060,
                        "low": 4.960,
                        "close": 5.048,
                        "volume": 100_000_000,
                        "amount": 504_800_000.0,
                    }
                ]
            )

        def fund_etf_dividend_sina(self, symbol: str) -> pd.DataFrame:
            assert symbol == "sh510300"
            return pd.DataFrame()

        def stock_zh_a_hist_tx(
            self, *, symbol: str, start_date: str, end_date: str
        ) -> pd.DataFrame:
            assert (symbol, start_date, end_date) == ("sh510300", "20260626", "20260626")
            return pd.DataFrame(
                [
                    {
                        "date": "2026-06-26",
                        "open": 5.008,
                        "close": 4.907,
                        "high": 5.015,
                        "low": 4.880,
                        "amount": 9_582_429.0,
                    }
                ]
            )

        def fund_etf_spot_em(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "代码": "510300",
                        "最新价": 4.907,
                        "开盘价": 5.008,
                        "最高价": 5.015,
                        "最低价": 4.880,
                        "成交量": 9_582_429.0,
                        "成交额": 4_730_764_080.0,
                        "数据日期": "2026-06-26",
                        "更新时间": "2026-06-26 16:11:54+08:00",
                    }
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2026-06-25", "2026-06-26"]})

    dataset = fetch_etf_dataset(
        symbol="510300.SH",
        name="沪深300ETF",
        start_date="20260625",
        end_date="20260626",
        client=SameDaySupplementAkshare(),
        updated_at=datetime(2026, 6, 26, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        retries=1,
    )

    bars = dataset["bars_1d"]
    assert bars["dt"].tolist() == [
        "2026-06-25T15:00:00+08:00",
        "2026-06-26T15:00:00+08:00",
    ]
    latest = bars.iloc[-1]
    assert float(latest["open"]) == 5.008
    assert float(latest["high"]) == 5.015
    assert float(latest["low"]) == 4.880
    assert float(latest["close"]) == 4.907
    assert float(latest["volume"]) == 958_242_900.0
    assert float(latest["amount"]) == 4_730_764_080.0
    assert latest["source"] == "akshare:fund_etf_hist_sina+tx_daily+fund_etf_spot_em"


def test_fetch_etf_dataset_rejects_same_day_supplement_when_sources_disagree() -> None:
    class MismatchedSameDayAkshare:
        def fund_etf_hist_em(
            self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
        ) -> pd.DataFrame:
            raise ConnectionError("eastmoney unavailable")

        def fund_etf_hist_sina(self, symbol: str) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "date": "2026-06-25",
                        "open": 4.970,
                        "high": 5.060,
                        "low": 4.960,
                        "close": 5.048,
                        "volume": 100_000_000,
                        "amount": 504_800_000.0,
                    }
                ]
            )

        def fund_etf_dividend_sina(self, symbol: str) -> pd.DataFrame:
            return pd.DataFrame()

        def stock_zh_a_hist_tx(
            self, *, symbol: str, start_date: str, end_date: str
        ) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "date": "2026-06-26",
                        "open": 5.008,
                        "close": 4.907,
                        "high": 5.015,
                        "low": 4.880,
                        "amount": 9_582_429.0,
                    }
                ]
            )

        def fund_etf_spot_em(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "代码": "510300",
                        "最新价": 4.906,
                        "开盘价": 5.008,
                        "最高价": 5.015,
                        "最低价": 4.880,
                        "成交量": 9_582_429.0,
                        "成交额": 4_730_764_080.0,
                        "数据日期": "2026-06-26",
                    }
                ]
            )

        def tool_trade_date_hist_sina(self) -> pd.DataFrame:
            return pd.DataFrame({"trade_date": ["2026-06-25", "2026-06-26"]})

    try:
        fetch_etf_dataset(
            symbol="510300.SH",
            name="沪深300ETF",
            start_date="20260625",
            end_date="20260626",
            client=MismatchedSameDayAkshare(),
            updated_at=datetime(2026, 6, 26, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
            retries=1,
        )
    except ValueError as error:
        assert "same-day supplement mismatch" in str(error)
    else:
        raise AssertionError("expected mismatched same-day supplement to be rejected")
