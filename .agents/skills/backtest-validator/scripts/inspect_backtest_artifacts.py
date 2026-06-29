#!/usr/bin/env python3
"""Inspect quant backtest artifacts for basic completeness.

This script checks file presence and parseability only. It does not decide
whether a strategy has edge or whether it should trade.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "equity": "equity.csv",
    "orders": "orders.csv",
    "trades": "trades.csv",
    "events": "events.jsonl",
    "report": "report.md",
    "config_snapshot": "config_snapshot.yaml",
}


def inspect_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "headers": [], "error": "missing"}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = 0
            for _ in reader:
                rows += 1
        return {
            "exists": True,
            "rows": rows,
            "headers": reader.fieldnames or [],
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {"exists": True, "rows": 0, "headers": [], "error": str(exc)}


def inspect_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "invalid_rows": 0, "types": {}, "error": "missing"}
    rows = 0
    invalid_rows = 0
    types: dict[str, int] = {}
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rows += 1
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    continue
                event_type = str(event.get("type", "unknown"))
                types[event_type] = types.get(event_type, 0) + 1
        return {
            "exists": True,
            "rows": rows,
            "invalid_rows": invalid_rows,
            "types": types,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {"exists": True, "rows": rows, "invalid_rows": invalid_rows, "types": types, "error": str(exc)}


def inspect_text(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "error": "missing"}
    try:
        text = path.read_text(encoding="utf-8-sig")
        return {"exists": True, "bytes": len(text.encode("utf-8")), "error": None}
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {"exists": True, "bytes": 0, "error": str(exc)}


def inspect_artifacts(artifact_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "artifact_dir": str(artifact_dir),
        "exists": artifact_dir.exists(),
        "files": {},
        "blocking_issues": [],
        "warnings": [],
    }
    if not artifact_dir.exists():
        result["blocking_issues"].append("artifact directory does not exist")
        result["status"] = "FAIL"
        return result

    for key, filename in REQUIRED_FILES.items():
        path = artifact_dir / filename
        if filename.endswith(".csv"):
            result["files"][key] = inspect_csv(path)
        elif filename.endswith(".jsonl"):
            result["files"][key] = inspect_jsonl(path)
        else:
            result["files"][key] = inspect_text(path)

    for key, info in result["files"].items():
        if not info.get("exists"):
            result["blocking_issues"].append(f"missing {REQUIRED_FILES[key]}")
        if info.get("error") and info.get("exists"):
            result["blocking_issues"].append(f"{REQUIRED_FILES[key]} parse/read error: {info['error']}")

    events = result["files"].get("events", {})
    if events.get("invalid_rows"):
        result["blocking_issues"].append(f"events.jsonl has {events['invalid_rows']} invalid JSON rows")

    equity = result["files"].get("equity", {})
    if equity.get("exists") and equity.get("rows", 0) < 20:
        result["warnings"].append("equity.csv has fewer than 20 rows")

    orders = result["files"].get("orders", {})
    trades = result["files"].get("trades", {})
    if orders.get("exists") and orders.get("rows", 0) == 0:
        result["warnings"].append("orders.csv has zero rows")
    if trades.get("exists") and trades.get("rows", 0) == 0:
        result["warnings"].append("trades.csv has zero rows")

    result["status"] = "FAIL" if result["blocking_issues"] else "PASS_WITH_WARNINGS" if result["warnings"] else "PASS"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect quant backtest artifacts.")
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()

    result = inspect_artifacts(args.artifact_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if result.get("blocking_issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
