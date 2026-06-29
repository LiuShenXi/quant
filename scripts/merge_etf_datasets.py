#!/usr/bin/env python3
"""Merge single-symbol ETF data roots into a multi-symbol research dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DATASET_FILES = {
    "bars_1d": "bars_1d.csv",
    "instruments": "instruments.csv",
    "adjust_factors": "adjust_factors.csv",
    "trade_calendar": "trade_calendar.csv",
}


def read_required_csv(data_root: Path, filename: str) -> pd.DataFrame:
    path = data_root / filename
    if not path.exists():
        raise FileNotFoundError(f"missing required dataset file: {path}")
    return pd.read_csv(path)


def merge_frames(input_roots: list[Path]) -> dict[str, pd.DataFrame]:
    frames = {
        key: [read_required_csv(root, filename) for root in input_roots]
        for key, filename in DATASET_FILES.items()
    }
    bars = pd.concat(frames["bars_1d"], ignore_index=True).sort_values(["dt", "symbol"])
    if bars.duplicated(["symbol", "dt"]).any():
        duplicates = bars[bars.duplicated(["symbol", "dt"], keep=False)][["symbol", "dt"]]
        raise ValueError(f"duplicate bars found: {duplicates.to_dict('records')[:5]}")

    instruments = (
        pd.concat(frames["instruments"], ignore_index=True)
        .drop_duplicates(["symbol"], keep="first")
        .sort_values(["symbol"])
    )
    if len(instruments) != len(set(instruments["symbol"])):
        raise ValueError("duplicate instrument symbols found")

    factors = pd.concat(frames["adjust_factors"], ignore_index=True).sort_values(
        ["symbol", "ex_date"]
    )
    if factors.duplicated(["symbol", "ex_date"]).any():
        duplicates = factors[factors.duplicated(["symbol", "ex_date"], keep=False)][
            ["symbol", "ex_date"]
        ]
        raise ValueError(f"duplicate factors found: {duplicates.to_dict('records')[:5]}")

    calendar = (
        pd.concat(frames["trade_calendar"], ignore_index=True)
        .drop_duplicates(["exchange", "date"], keep="first")
        .sort_values(["exchange", "date"])
    )
    return {
        "bars_1d": bars.reset_index(drop=True),
        "instruments": instruments.reset_index(drop=True),
        "adjust_factors": factors.reset_index(drop=True),
        "trade_calendar": calendar.reset_index(drop=True),
    }


def write_dataset(dataset: dict[str, pd.DataFrame], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for key, filename in DATASET_FILES.items():
        dataset[key].to_csv(out / filename, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge ETF data_root directories.")
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    dataset = merge_frames(args.input)
    write_dataset(dataset, args.out)
    print(f"merged data_root: {args.out}")
    print(f"bars: {len(dataset['bars_1d'])}")
    print(f"instruments: {len(dataset['instruments'])}")
    print(f"adjust_factors: {len(dataset['adjust_factors'])}")
    print(f"calendar days: {len(dataset['trade_calendar'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
