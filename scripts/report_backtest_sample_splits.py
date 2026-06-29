#!/usr/bin/env python3
"""Generate deterministic sample-split metrics for a backtest and benchmarks.

This report is research evidence only. It is not investment advice or trading
permission.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def day_key(timestamp: str) -> str:
    return timestamp.split("T", 1)[0]


def round4(value: float) -> float:
    return round(value, 4)


def max_drawdown_pct(values: list[float]) -> float:
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak if peak else 0.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return round4(max_drawdown * 100)


def metrics(values: list[float]) -> dict[str, float]:
    return {
        "return_pct": round4((values[-1] / values[0] - 1) * 100),
        "max_drawdown_pct": max_drawdown_pct(values),
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_daily_equity(artifact_dir: Path) -> dict[str, dict[str, str]]:
    daily: dict[str, dict[str, str]] = {}
    for row in read_csv_rows(artifact_dir / "equity.csv"):
        daily[day_key(row["dt"])] = row
    return daily


def load_bars(data_root: Path, symbols: list[str]) -> dict[str, dict[str, dict[str, str]]]:
    bars = {symbol: {} for symbol in symbols}
    for row in read_csv_rows(data_root / "bars_1d.csv"):
        symbol = row.get("symbol")
        if symbol in bars and row.get("data_status", "ok") == "ok":
            bars[symbol][day_key(row["dt"])] = row
    for symbol, rows in bars.items():
        if not rows:
            raise ValueError(f"no bars for {symbol}")
    return bars


def split_dates(dates: list[str]) -> dict[str, list[str]]:
    mid = len(dates) // 2
    return {
        "first_half": dates[:mid],
        "second_half": dates[mid:],
    }


def benchmark_metrics(
    bars: dict[str, dict[str, dict[str, str]]],
    dates: list[str],
) -> dict[str, Any]:
    benchmarks: dict[str, Any] = {}
    for symbol in sorted(bars):
        closes = [float(bars[symbol][date]["close"]) for date in dates]
        normalized = [100000.0 * close / closes[0] for close in closes]
        benchmarks[symbol] = {
            **metrics(normalized),
            "rows": len(normalized),
        }

    first_close = {
        symbol: float(bars[symbol][dates[0]]["close"])
        for symbol in bars
    }
    equal_weight = []
    for date in dates:
        ratios = [
            float(bars[symbol][date]["close"]) / first_close[symbol]
            for symbol in bars
        ]
        equal_weight.append(100000.0 * sum(ratios) / len(ratios))
    benchmarks["equal_weight"] = {
        **metrics(equal_weight),
        "rows": len(equal_weight),
        "symbols": sorted(bars),
    }
    return benchmarks


def build_report(artifact_dir: Path, data_root: Path, symbols: list[str]) -> dict[str, Any]:
    daily_equity = load_daily_equity(artifact_dir)
    bars = load_bars(data_root, symbols)
    common_dates = sorted(
        set(daily_equity).intersection(*(set(bars[symbol]) for symbol in symbols))
    )
    if len(common_dates) < 2:
        raise ValueError("not enough common dates for sample split")

    splits: dict[str, Any] = {}
    for name, dates in split_dates(common_dates).items():
        equity_rows = [daily_equity[date] for date in dates]
        equity_values = [float(row["total_value"]) for row in equity_rows]
        splits[name] = {
            "period": {
                "start": equity_rows[0]["dt"],
                "end": equity_rows[-1]["dt"],
                "rows": len(equity_rows),
            },
            "strategy": metrics(equity_values),
            "benchmarks": benchmark_metrics(bars, dates),
        }

    return {
        "artifact_dir": str(artifact_dir),
        "data_root": str(data_root),
        "status": "PASS",
        "not_trading_permission": True,
        "method": "unique_date_halves_daily_last_equity",
        "splits": splits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sample-split backtest metrics.")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()

    try:
        report = build_report(args.artifact_dir, args.data_root, args.symbols)
    except Exception as exc:
        report = {
            "artifact_dir": str(args.artifact_dir),
            "data_root": str(args.data_root),
            "status": "FAIL",
            "not_trading_permission": True,
            "blocking_issues": [str(exc)],
        }
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
