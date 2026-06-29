#!/usr/bin/env python3
"""Generate a deterministic summary report for backtest artifacts.

This report is research evidence only. It is not paper approval, live approval,
investment advice, or trading permission.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from inspect_backtest_artifacts import inspect_artifacts


REQUIRED_FILENAMES = [
    "equity.csv",
    "orders.csv",
    "trades.csv",
    "events.jsonl",
    "report.md",
    "config_snapshot.yaml",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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


def build_report(artifact_dir: Path) -> dict[str, Any]:
    inspection = inspect_artifacts(artifact_dir)
    if inspection["blocking_issues"]:
        return {
            "artifact_dir": str(artifact_dir),
            "status": "FAIL",
            "not_trading_permission": True,
            "inspection": inspection,
        }

    equity = read_csv_rows(artifact_dir / "equity.csv")
    orders = read_csv_rows(artifact_dir / "orders.csv")
    trades = read_csv_rows(artifact_dir / "trades.csv")
    total_values = [float(row["total_value"]) for row in equity]
    initial_value = total_values[0]
    final_value = total_values[-1]

    report = {
        "artifact_dir": str(artifact_dir),
        "status": inspection["status"],
        "not_trading_permission": True,
        "period": {
            "start": equity[0]["dt"],
            "end": equity[-1]["dt"],
            "equity_rows": len(equity),
        },
        "metrics": {
            "initial_value": round4(initial_value),
            "final_value": round4(final_value),
            "return_pct": round4((final_value / initial_value - 1) * 100),
            "max_drawdown_pct": max_drawdown_pct(total_values),
        },
        "orders": {
            "rows": len(orders),
            "rejected": sum(1 for row in orders if row.get("status") == "REJECTED"),
        },
        "trades": {
            "rows": len(trades),
            "symbols": sorted({row["symbol"] for row in trades if row.get("symbol")}),
        },
        "costs": {
            "total_commission": round4(sum(float(row.get("commission") or 0) for row in trades)),
        },
        "hashes": {
            filename: sha256(artifact_dir / filename)
            for filename in REQUIRED_FILENAMES
            if (artifact_dir / filename).exists()
        },
        "inspection": inspection,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a backtest artifact report.")
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()

    report = build_report(args.artifact_dir)
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
