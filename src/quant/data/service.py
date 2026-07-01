from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from quant.core.contract import Bar, Instrument
from quant.data.calendar import MarketCalendar
from quant.data.manifest import DatasetManifest, FrequencyManifest, SymbolManifest
from quant.data.quality import reject_missing_rows


class DataService:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        manifest_path = data_root / "dataset_manifest.yaml"
        self._manifest = DatasetManifest.load(manifest_path) if manifest_path.exists() else None
        self._timezone = (
            ZoneInfo(self._manifest.timezone)
            if self._manifest is not None
            else ZoneInfo("Asia/Shanghai")
        )
        self._calendar = self._load_calendar()
        self._bars_by_freq = self._load_frequency_bars()
        primary_freq = "1d" if "1d" in self._bars_by_freq else next(iter(self._bars_by_freq))
        self._bars = self._bars_by_freq[primary_freq]
        self._instruments = pd.read_csv(
            data_root / "instruments.csv",
            parse_dates=["list_date", "delist_date"],
        )
        factors_path = data_root / "adjust_factors.csv"
        self._factors = (
            pd.read_csv(factors_path, parse_dates=["ex_date"])
            if factors_path.exists()
            else pd.DataFrame(columns=["symbol", "ex_date", "factor"])
        )

    def load_bars(self, universe: list[str], freq: str = "1d") -> list[Bar]:
        if not universe:
            return []

        source = self._bars_for_frequency(freq)
        frame = source[source["symbol"].isin(universe)].copy()
        frame = frame.sort_values(["dt", "symbol"])
        reject_missing_rows(frame)
        self._reject_missing_expected_bars(frame=frame, universe=universe, freq=freq)
        frame = frame[frame["data_status"] == "ok"]
        return [
            Bar(
                symbol=row.symbol,
                freq=freq,
                dt=_ensure_timezone_aware(row.dt, self._timezone),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                amount=float(row.amount),
                pre_close=_optional_float(row.pre_close),
                limit_up=_optional_float(row.limit_up),
                limit_down=_optional_float(row.limit_down),
                suspended=bool(row.suspended),
            )
            for row in frame.itertuples(index=False)
        ]

    def history(
        self,
        symbol: str,
        end: datetime,
        n: int,
        freq: str = "1d",
        adjust: str = "qfq",
        fields: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        source = self._bars_for_frequency(freq)
        end = _ensure_timezone_aware(end, self._timezone)
        frame = source[(source["symbol"] == symbol) & (source["dt"] <= end)].copy()
        frame = frame.sort_values("dt").tail(n)
        reject_missing_rows(frame)
        if adjust == "qfq":
            if self._has_adjust_factors(symbol):
                frame = self._apply_qfq(frame, symbol=symbol, end=end)
            elif self._manifest is None:
                raise ValueError(f"no adjust factors for {symbol} as of {end}")
        elif adjust != "raw":
            raise ValueError(f"unsupported adjust={adjust}")
        columns = ["symbol", "dt", "open", "high", "low", "close", "volume", "amount"]
        if fields is not None:
            columns = ["dt", *fields]
        return frame[columns].reset_index(drop=True)

    def latest_bar_time(self, symbol: str, freq: str = "1d") -> datetime | None:
        source = self._bars_for_frequency(freq)
        frame = source[source["symbol"] == symbol]
        if frame.empty:
            return None
        return _ensure_timezone_aware(frame["dt"].max(), self._timezone)

    def get_instrument(self, symbol: str) -> Instrument:
        row = self._instruments[self._instruments["symbol"] == symbol].iloc[0]
        delist = row["delist_date"]
        return Instrument(
            symbol=row["symbol"],
            name=row["name"],
            type=row["type"],
            exchange=row["exchange"],
            list_date=row["list_date"].date(),
            delist_date=None if pd.isna(delist) else delist.date(),
            lot_size=int(row["lot_size"]),
            qty_step=int(row["qty_step"]),
            tick_size=float(row["tick_size"]),
            t_plus=int(row["t_plus"]),
            status=row["status"],
        )

    def _load_frequency_bars(self) -> dict[str, pd.DataFrame]:
        if self._manifest is None:
            return {"1d": _read_bar_file(self.data_root / "bars_1d.csv")}
        return {
            frequency.freq: _read_bar_file(self.data_root / frequency.file)
            for frequency in self._manifest.frequencies
        }

    def _load_calendar(self) -> MarketCalendar | None:
        if self._manifest is None:
            return None
        if self._manifest.calendar == "continuous_24x7":
            return MarketCalendar.continuous_24x7(timezone=self._manifest.timezone)
        raise ValueError(f"unsupported dataset calendar {self._manifest.calendar!r}")

    def _bars_for_frequency(self, freq: str) -> pd.DataFrame:
        if freq in self._bars_by_freq:
            return self._bars_by_freq[freq]
        if self._manifest is None:
            raise ValueError("v1 supports daily bars only")
        self._manifest.expected_frequency(freq)
        raise ValueError(f"frequency {freq!r} is not loaded")

    def _reject_missing_expected_bars(
        self,
        *,
        frame: pd.DataFrame,
        universe: list[str],
        freq: str,
    ) -> None:
        if self._manifest is None or self._calendar is None:
            return
        frequency = self._manifest.expected_frequency(freq)
        for symbol in universe:
            symbol_manifest = self._symbol_manifest(symbol)
            if symbol_manifest is None:
                continue
            missing = self._missing_expected_timestamps(
                frame=frame,
                symbol=symbol,
                symbol_manifest=symbol_manifest,
                frequency=frequency,
            )
            if missing:
                joined = ", ".join(timestamp.isoformat() for timestamp in missing[:5])
                raise ValueError(f"{freq} bars missing for {symbol}: {joined}")

    def _missing_expected_timestamps(
        self,
        *,
        frame: pd.DataFrame,
        symbol: str,
        symbol_manifest: SymbolManifest,
        frequency: FrequencyManifest,
    ) -> list[datetime]:
        start = max(frequency.coverage.start, symbol_manifest.active_from)
        end = frequency.coverage.end
        if symbol_manifest.active_to is not None:
            end = min(end, symbol_manifest.active_to)
        if end < start:
            return []
        expected = self._calendar.expected_timestamps(start=start, end=end, freq=frequency.freq)
        actual = {
            _ensure_timezone_aware(value, self._timezone).astimezone(self._timezone)
            for value in frame[frame["symbol"] == symbol]["dt"]
        }
        return [timestamp for timestamp in expected if timestamp not in actual]

    def _symbol_manifest(self, symbol: str) -> SymbolManifest | None:
        if self._manifest is None:
            return None
        for candidate in self._manifest.symbols:
            if candidate.symbol == symbol:
                return candidate
        return None

    def _has_adjust_factors(self, symbol: str) -> bool:
        if self._factors.empty:
            return False
        return not self._factors[self._factors["symbol"] == symbol].empty

    def _apply_qfq(self, frame: pd.DataFrame, symbol: str, end: datetime) -> pd.DataFrame:
        factors = self._factors[self._factors["symbol"] == symbol].copy()
        factors = factors[factors["ex_date"].dt.date <= end.date()]
        if factors.empty:
            raise ValueError(f"no adjust factors for {symbol} as of {end}")
        base = float(factors.sort_values("ex_date").iloc[-1]["factor"])
        frame["factor_date"] = pd.to_datetime(frame["dt"].dt.date)
        merged = frame.merge(
            factors[["ex_date", "factor"]],
            left_on="factor_date",
            right_on="ex_date",
            how="left",
        )
        merged["factor"] = merged["factor"].ffill().bfill()
        for column in ["open", "high", "low", "close"]:
            merged[column] = merged[column] * merged["factor"] / base
        return merged.drop(columns=["factor_date", "ex_date", "factor"])


def _read_bar_file(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for column in ["dt", "updated_at"]:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column])
    return frame


def _ensure_timezone_aware(value: datetime, timezone: ZoneInfo | None = None) -> datetime:
    aware = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    fallback = timezone if timezone is not None else ZoneInfo("Asia/Shanghai")
    if aware.tzinfo is None or aware.utcoffset() is None:
        return aware.replace(tzinfo=fallback)
    return aware


def _optional_float(value: object) -> float | None:
    if value == "" or pd.isna(value):
        return None
    return float(value)
