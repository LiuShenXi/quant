from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta
from datetime import time as datetime_time
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import pandas as pd

DATASET_FILES = {
    "bars_1d": "bars_1d.csv",
    "instruments": "instruments.csv",
    "adjust_factors": "adjust_factors.csv",
    "trade_calendar": "trade_calendar.csv",
}

SAME_DAY_BAR_ACCEPT_TIME = datetime_time(hour=15, minute=10)


class AkshareEtfClient(Protocol):
    def fund_etf_hist_em(
        self, *, symbol: str, period: str, start_date: str, end_date: str, adjust: str
    ) -> pd.DataFrame: ...

    def tool_trade_date_hist_sina(self) -> pd.DataFrame: ...

    def fund_etf_hist_sina(self, symbol: str) -> pd.DataFrame: ...

    def fund_etf_dividend_sina(self, symbol: str) -> pd.DataFrame: ...

    def stock_zh_a_hist_tx(
        self, *, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...

    def fund_etf_spot_em(self) -> pd.DataFrame: ...


def fetch_etf_dataset(
    *,
    symbol: str,
    name: str,
    start_date: str,
    end_date: str,
    client: AkshareEtfClient | None = None,
    updated_at: datetime | None = None,
    retries: int = 3,
    retry_delay_sec: float = 1.0,
) -> dict[str, pd.DataFrame]:
    updated_at = updated_at or datetime.now(tz=ZoneInfo("Asia/Shanghai"))
    effective_end_date = _complete_daily_end_date(end_date=end_date, updated_at=updated_at)
    if client is None:
        try:
            import akshare as client
        except ImportError as error:
            raise RuntimeError(
                "akshare is required for fetching real ETF data; install the data extra first"
            ) from error
    akshare_symbol = symbol.split(".")[0]
    source = "akshare:fund_etf_hist_em"
    try:
        raw_bars = _call_with_retries(
            lambda: client.fund_etf_hist_em(
                symbol=akshare_symbol,
                period="daily",
                start_date=start_date,
                end_date=effective_end_date,
                adjust="",
            ),
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        )
        qfq_bars = _call_with_retries(
            lambda: client.fund_etf_hist_em(
                symbol=akshare_symbol,
                period="daily",
                start_date=start_date,
                end_date=effective_end_date,
                adjust="qfq",
            ),
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        )
    except Exception:
        source = "akshare:fund_etf_hist_sina"
        raw_bars = _fetch_sina_bars(
            client,
            symbol=symbol,
            start_date=start_date,
            end_date=effective_end_date,
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        )
        raw_bars, source = _supplement_same_day_sina_bars(
            client,
            raw_bars=raw_bars,
            symbol=symbol,
            end_date=effective_end_date,
            updated_at=updated_at,
            source=source,
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        )
        qfq_bars = _build_sina_qfq_bars_from_dividends(
            client,
            raw_bars=raw_bars,
            symbol=symbol,
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        )
    raw_bars = _filter_bars_through_end_date(raw_bars, end_date=effective_end_date)
    if qfq_bars is not None:
        qfq_bars = _filter_bars_through_end_date(qfq_bars, end_date=effective_end_date)
    trade_calendar = _slice_trade_calendar(
        _call_with_retries(
            client.tool_trade_date_hist_sina,
            retries=retries,
            retry_delay_sec=retry_delay_sec,
        ),
        start_date=start_date,
        end_date=effective_end_date,
    )
    return build_etf_dataset(
        raw_bars=raw_bars,
        qfq_bars=qfq_bars,
        trade_calendar=trade_calendar,
        symbol=symbol,
        name=name,
        updated_at=updated_at,
        source=source,
    )


def _complete_daily_end_date(*, end_date: str, updated_at: datetime) -> str:
    shanghai_now = _as_shanghai_time(updated_at)
    requested_end = pd.to_datetime(end_date).date()
    if requested_end >= shanghai_now.date() and shanghai_now.time() < SAME_DAY_BAR_ACCEPT_TIME:
        return (shanghai_now.date() - timedelta(days=1)).strftime("%Y%m%d")
    return end_date


def _as_shanghai_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return value.astimezone(ZoneInfo("Asia/Shanghai"))


def _filter_bars_through_end_date(raw_bars: pd.DataFrame, *, end_date: str) -> pd.DataFrame:
    frame = raw_bars.copy()
    frame["日期"] = pd.to_datetime(frame["日期"])
    end = pd.to_datetime(end_date)
    frame = frame[frame["日期"] <= end].copy()
    frame["日期"] = frame["日期"].dt.strftime("%Y-%m-%d")
    return frame.reset_index(drop=True)


def _call_with_retries(
    call: Callable[[], pd.DataFrame], *, retries: int, retry_delay_sec: float
) -> pd.DataFrame:
    attempts = max(1, retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as error:
            last_error = error
            if attempt == attempts:
                break
            time.sleep(retry_delay_sec)
    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable retry state")


def _fetch_sina_bars(
    client: AkshareEtfClient,
    *,
    symbol: str,
    start_date: str,
    end_date: str,
    retries: int,
    retry_delay_sec: float,
) -> pd.DataFrame:
    exchange, code = symbol.split(".")[1].lower(), symbol.split(".")[0]
    frame = _call_with_retries(
        lambda: client.fund_etf_hist_sina(f"{exchange}{code}"),
        retries=retries,
        retry_delay_sec=retry_delay_sec,
    )
    frame = frame.rename(
        columns={
            "date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "volume": "成交量",
            "amount": "成交额",
        }
    )
    frame["日期"] = pd.to_datetime(frame["日期"])
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    frame = frame[(frame["日期"] >= start) & (frame["日期"] <= end)].copy()
    frame["成交量"] = frame["成交量"].astype(float) / 100
    frame["日期"] = frame["日期"].dt.strftime("%Y-%m-%d")
    return frame[["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额"]].reset_index(
        drop=True
    )


def _supplement_same_day_sina_bars(
    client: AkshareEtfClient,
    *,
    raw_bars: pd.DataFrame,
    symbol: str,
    end_date: str,
    updated_at: datetime,
    source: str,
    retries: int,
    retry_delay_sec: float,
) -> tuple[pd.DataFrame, str]:
    requested_end = pd.to_datetime(end_date).date()
    shanghai_now = _as_shanghai_time(updated_at)
    if requested_end != shanghai_now.date():
        return raw_bars, source
    if shanghai_now.time() < SAME_DAY_BAR_ACCEPT_TIME:
        return raw_bars, source
    if not hasattr(client, "stock_zh_a_hist_tx") or not hasattr(client, "fund_etf_spot_em"):
        return raw_bars, source

    frame = raw_bars.copy()
    frame["日期"] = pd.to_datetime(frame["日期"])
    if not frame.empty and frame["日期"].max().date() >= requested_end:
        frame["日期"] = frame["日期"].dt.strftime("%Y-%m-%d")
        return frame.reset_index(drop=True), source

    supplement = _fetch_cross_checked_same_day_bar(
        client,
        symbol=symbol,
        date=end_date,
        retries=retries,
        retry_delay_sec=retry_delay_sec,
    )
    frame = pd.concat([frame, supplement], ignore_index=True)
    frame["日期"] = pd.to_datetime(frame["日期"]).dt.strftime("%Y-%m-%d")
    return (
        frame.sort_values("日期").reset_index(drop=True),
        "akshare:fund_etf_hist_sina+tx_daily+fund_etf_spot_em",
    )


def _fetch_cross_checked_same_day_bar(
    client: AkshareEtfClient,
    *,
    symbol: str,
    date: str,
    retries: int,
    retry_delay_sec: float,
) -> pd.DataFrame:
    vendor_symbol = _vendor_symbol(symbol)
    tx_daily = _call_with_retries(
        lambda: client.stock_zh_a_hist_tx(
            symbol=vendor_symbol,
            start_date=date,
            end_date=date,
        ),
        retries=retries,
        retry_delay_sec=retry_delay_sec,
    )
    spot = _call_with_retries(
        client.fund_etf_spot_em,
        retries=retries,
        retry_delay_sec=retry_delay_sec,
    )

    requested_date = pd.to_datetime(date).date()
    tx_row = _select_tx_daily_row(tx_daily, requested_date=requested_date)
    spot_row = _select_spot_row(spot, symbol=symbol, requested_date=requested_date)
    _validate_cross_checked_same_day_row(tx_row=tx_row, spot_row=spot_row)

    return pd.DataFrame(
        [
            {
                "日期": requested_date.strftime("%Y-%m-%d"),
                "开盘": float(tx_row["open"]),
                "收盘": float(tx_row["close"]),
                "最高": float(tx_row["high"]),
                "最低": float(tx_row["low"]),
                "成交量": float(spot_row["成交量"]),
                "成交额": float(spot_row["成交额"]),
            }
        ]
    )


def _vendor_symbol(symbol: str) -> str:
    exchange, code = symbol.split(".")[1].lower(), symbol.split(".")[0]
    return f"{exchange}{code}"


def _select_tx_daily_row(tx_daily: pd.DataFrame, *, requested_date: object) -> pd.Series:
    if tx_daily.empty:
        raise ValueError("same-day supplement missing tx daily bar")
    frame = tx_daily.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    matched = frame[frame["date"] == requested_date]
    if matched.empty:
        raise ValueError("same-day supplement missing tx daily bar")
    return matched.iloc[-1]


def _select_spot_row(
    spot: pd.DataFrame, *, symbol: str, requested_date: object
) -> pd.Series:
    code = symbol.split(".")[0]
    matched = spot[spot["代码"].astype(str).str.zfill(6) == code]
    if matched.empty:
        raise ValueError("same-day supplement missing ETF spot row")
    row = matched.iloc[-1]
    if pd.to_datetime(row["数据日期"]).date() != requested_date:
        raise ValueError("same-day supplement spot date mismatch")
    return row


def _validate_cross_checked_same_day_row(*, tx_row: pd.Series, spot_row: pd.Series) -> None:
    comparisons = {
        "open": (tx_row["open"], spot_row["开盘价"]),
        "high": (tx_row["high"], spot_row["最高价"]),
        "low": (tx_row["low"], spot_row["最低价"]),
        "close": (tx_row["close"], spot_row["最新价"]),
    }
    for field, (tx_value, spot_value) in comparisons.items():
        if not _price_matches(tx_value, spot_value):
            raise ValueError(
                "same-day supplement mismatch: "
                f"{field} tx={float(tx_value)} spot={float(spot_value)}"
            )
    if float(spot_row["成交量"]) <= 0 or float(spot_row["成交额"]) <= 0:
        raise ValueError("same-day supplement spot volume/amount missing")
    if not _volume_matches(tx_row["amount"], spot_row["成交量"]):
        raise ValueError(
            "same-day supplement mismatch: "
            f"volume tx={float(tx_row['amount'])} spot={float(spot_row['成交量'])}"
        )


def _price_matches(left: object, right: object) -> bool:
    return round(float(left), 3) == round(float(right), 3)


def _volume_matches(left: object, right: object) -> bool:
    left_value = float(left)
    right_value = float(right)
    return abs(left_value - right_value) <= max(1.0, abs(right_value) * 0.001)


def _build_sina_qfq_bars_from_dividends(
    client: AkshareEtfClient,
    *,
    raw_bars: pd.DataFrame,
    symbol: str,
    retries: int,
    retry_delay_sec: float,
) -> pd.DataFrame | None:
    if not hasattr(client, "fund_etf_dividend_sina"):
        return None
    exchange, code = symbol.split(".")[1].lower(), symbol.split(".")[0]
    dividends = _call_with_retries(
        lambda: client.fund_etf_dividend_sina(f"{exchange}{code}"),
        retries=retries,
        retry_delay_sec=retry_delay_sec,
    )
    if dividends.empty or "日期" not in dividends or "累计分红" not in dividends:
        return None

    raw = raw_bars.copy()
    raw["日期"] = pd.to_datetime(raw["日期"])
    dividends = dividends.copy()
    dividends["日期"] = pd.to_datetime(dividends["日期"])
    dividends = dividends.sort_values("日期").reset_index(drop=True)
    latest_cumulative = _cumulative_dividend_as_of(dividends, raw["日期"].max())

    adjusted = raw.copy()
    for index, row in raw.iterrows():
        cumulative = _cumulative_dividend_as_of(dividends, row["日期"])
        cash_adjustment = latest_cumulative - cumulative
        for column in ["开盘", "收盘", "最高", "最低"]:
            adjusted.at[index, column] = float(row[column]) - cash_adjustment
    adjusted["日期"] = adjusted["日期"].dt.strftime("%Y-%m-%d")
    return adjusted


def _cumulative_dividend_as_of(dividends: pd.DataFrame, when: pd.Timestamp) -> float:
    eligible = dividends[dividends["日期"] <= when]
    if eligible.empty:
        return 0.0
    return float(eligible.iloc[-1]["累计分红"])


def build_etf_dataset(
    *,
    raw_bars: pd.DataFrame,
    qfq_bars: pd.DataFrame | None,
    trade_calendar: pd.DataFrame,
    symbol: str,
    name: str,
    updated_at: datetime,
    source: str,
) -> dict[str, pd.DataFrame]:
    bars = _build_bars(raw_bars, symbol=symbol, updated_at=updated_at, source=source)
    instruments = _build_instruments(symbol=symbol, name=name, list_date=bars.iloc[0]["dt"][:10])
    factors = _build_adjust_factors(raw_bars=raw_bars, qfq_bars=qfq_bars, symbol=symbol)
    calendar = _build_trade_calendar(trade_calendar, exchange=symbol.split(".")[1])
    return {
        "bars_1d": bars,
        "instruments": instruments,
        "adjust_factors": factors,
        "trade_calendar": calendar,
    }


def write_dataset(dataset: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in DATASET_FILES.items():
        dataset[key].to_csv(output_dir / filename, index=False)


def _build_bars(
    raw_bars: pd.DataFrame,
    *,
    symbol: str,
    updated_at: datetime,
    source: str,
) -> pd.DataFrame:
    frame = raw_bars.copy()
    frame["日期"] = pd.to_datetime(frame["日期"])
    frame = frame.sort_values("日期").reset_index(drop=True)
    pre_close = frame["收盘"].shift(1).fillna(frame["收盘"])
    updated = _iso(updated_at)
    bars = pd.DataFrame(
        {
            "symbol": symbol,
            "dt": frame["日期"].map(_market_close_iso),
            "open": frame["开盘"].astype(float),
            "high": frame["最高"].astype(float),
            "low": frame["最低"].astype(float),
            "close": frame["收盘"].astype(float),
            "volume": frame["成交量"].astype(float) * 100,
            "amount": frame["成交额"].astype(float),
            "pre_close": pre_close.astype(float),
            "limit_up": (pre_close.astype(float) * 1.10).round(3),
            "limit_down": (pre_close.astype(float) * 0.90).round(3),
            "suspended": False,
            "data_status": "ok",
            "source": source,
            "updated_at": updated,
        }
    )
    return bars


def _build_instruments(*, symbol: str, name: str, list_date: str) -> pd.DataFrame:
    exchange = symbol.split(".")[1]
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "name": name,
                "type": "etf",
                "exchange": exchange,
                "list_date": list_date,
                "delist_date": "",
                "lot_size": 100,
                "qty_step": 100,
                "tick_size": 0.001,
                "t_plus": 1,
                "status": "active",
            }
        ]
    )


def _build_adjust_factors(
    *, raw_bars: pd.DataFrame, qfq_bars: pd.DataFrame | None, symbol: str
) -> pd.DataFrame:
    raw = raw_bars[["日期", "收盘"]].copy()
    raw["日期"] = pd.to_datetime(raw["日期"])
    raw = raw.sort_values("日期").reset_index(drop=True)
    if qfq_bars is None:
        factors = pd.Series([1.0] * len(raw), index=raw.index)
    else:
        qfq = qfq_bars[["日期", "收盘"]].copy()
        qfq["日期"] = pd.to_datetime(qfq["日期"])
        qfq = qfq.sort_values("日期").reset_index(drop=True)
        factors = qfq["收盘"].astype(float) / raw["收盘"].astype(float)
        factors = factors / float(factors.iloc[-1])
    return pd.DataFrame(
        {
            "symbol": symbol,
            "ex_date": raw["日期"].dt.strftime("%Y-%m-%d"),
            "factor": factors.astype(float),
        }
    )


def _build_trade_calendar(trade_calendar: pd.DataFrame, *, exchange: str) -> pd.DataFrame:
    frame = trade_calendar.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    frame = frame.sort_values("trade_date").reset_index(drop=True)
    return pd.DataFrame(
        {
            "exchange": exchange,
            "date": frame["trade_date"].dt.strftime("%Y-%m-%d"),
            "is_open": True,
        }
    )


def _slice_trade_calendar(
    trade_calendar: pd.DataFrame, *, start_date: str, end_date: str
) -> pd.DataFrame:
    frame = trade_calendar.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    return frame[(frame["trade_date"] >= start) & (frame["trade_date"] <= end)].reset_index(
        drop=True
    )


def _market_close_iso(value: pd.Timestamp) -> str:
    close_time = value.to_pydatetime().replace(hour=15, minute=0, second=0, microsecond=0)
    return close_time.replace(tzinfo=ZoneInfo("Asia/Shanghai")).isoformat()


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return value.isoformat()
