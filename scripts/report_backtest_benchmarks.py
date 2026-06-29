#!/usr/bin/env python3
"""Generate deterministic close-to-close benchmark metrics for a dataset.

The output is research evidence only. It is not investment advice or trading
permission.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


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


def load_bars(data_root: Path, symbols: list[str]) -> dict[str, list[dict[str, str]]]:
    bars_path = data_root / "bars_1d.csv"
    with bars_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_symbol: dict[str, list[dict[str, str]]] = {symbol: [] for symbol in symbols}
    for row in rows:
        symbol = row.get("symbol")
        if symbol in by_symbol and row.get("data_status", "ok") == "ok":
            by_symbol[symbol].append(row)

    for symbol, symbol_rows in by_symbol.items():
        if not symbol_rows:
            raise ValueError(f"no bars for {symbol}")
        symbol_rows.sort(key=lambda row: row["dt"])
    return by_symbol


def normalized_equity(rows: list[dict[str, str]], initial_value: float = 100000.0) -> list[float]:
    first_close = float(rows[0]["close"])
    return [initial_value * float(row["close"]) / first_close for row in rows]


def benchmark_one(rows: list[dict[str, str]]) -> dict[str, Any]:
    equity = normalized_equity(rows)
    return {
        "start": rows[0]["dt"],
        "end": rows[-1]["dt"],
        "rows": len(rows),
        "return_pct": round4((equity[-1] / equity[0] - 1) * 100),
        "max_drawdown_pct": max_drawdown_pct(equity),
    }


def equal_weight_benchmark(by_symbol: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    symbols = sorted(by_symbol)
    dates = sorted(set.intersection(*(set(row["dt"] for row in by_symbol[s]) for s in symbols)))
    if not dates:
        raise ValueError("no common dates across benchmark symbols")

    row_by_symbol_date = {
        symbol: {row["dt"]: row for row in rows}
        for symbol, rows in by_symbol.items()
    }
    first_close = {
        symbol: float(row_by_symbol_date[symbol][dates[0]]["close"])
        for symbol in symbols
    }

    equity = []
    for date in dates:
        ratios = [
            float(row_by_symbol_date[symbol][date]["close"]) / first_close[symbol]
            for symbol in symbols
        ]
        equity.append(100000.0 * sum(ratios) / len(ratios))

    return {
        "start": dates[0],
        "end": dates[-1],
        "rows": len(dates),
        "symbols": symbols,
        "return_pct": round4((equity[-1] / equity[0] - 1) * 100),
        "max_drawdown_pct": max_drawdown_pct(equity),
    }


def build_report(data_root: Path, symbols: list[str]) -> dict[str, Any]:
    by_symbol = load_bars(data_root, symbols)
    benchmarks = {
        symbol: benchmark_one(by_symbol[symbol])
        for symbol in symbols
    }
    benchmarks["equal_weight"] = equal_weight_benchmark(by_symbol)
    equal_weight = benchmarks["equal_weight"]
    return {
        "data_root": str(data_root),
        "status": "PASS",
        "not_trading_permission": True,
        "method": "close_to_close_normalized_buy_and_hold",
        "period": {
            "start": equal_weight["start"],
            "end": equal_weight["end"],
            "rows": equal_weight["rows"],
        },
        "benchmarks": benchmarks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate close-to-close benchmark metrics.")
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()

    try:
        report = build_report(args.data_root, args.symbols)
    except Exception as exc:
        report = {
            "data_root": str(args.data_root),
            "status": "FAIL",
            "not_trading_permission": True,
            "blocking_issues": [str(exc)],
        }
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
