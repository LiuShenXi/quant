from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import pandas as pd

from quant.core.contract import Instrument
from quant.data.quality import reject_missing_rows


class DataService:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self._bars = pd.read_csv(data_root / "bars_1d.csv", parse_dates=["dt", "updated_at"])
        self._instruments = pd.read_csv(
            data_root / "instruments.csv",
            parse_dates=["list_date", "delist_date"],
        )
        self._factors = pd.read_csv(data_root / "adjust_factors.csv", parse_dates=["ex_date"])

    def history(
        self,
        symbol: str,
        end: datetime,
        n: int,
        freq: str = "1d",
        adjust: str = "qfq",
        fields: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        if freq != "1d":
            raise ValueError("v1 supports daily bars only")
        frame = self._bars[(self._bars["symbol"] == symbol) & (self._bars["dt"] <= end)].copy()
        frame = frame.sort_values("dt").tail(n)
        reject_missing_rows(frame)
        if adjust == "qfq":
            frame = self._apply_qfq(frame, symbol=symbol, end=end)
        elif adjust != "raw":
            raise ValueError(f"unsupported adjust={adjust}")
        columns = ["symbol", "dt", "open", "high", "low", "close", "volume", "amount"]
        if fields is not None:
            columns = ["dt", *fields]
        return frame[columns].reset_index(drop=True)

    def latest_bar_time(self, symbol: str, freq: str = "1d") -> datetime | None:
        if freq != "1d":
            raise ValueError("v1 supports daily bars only")
        frame = self._bars[self._bars["symbol"] == symbol]
        if frame.empty:
            return None
        return frame["dt"].max().to_pydatetime()

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
