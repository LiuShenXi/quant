#!/usr/bin/env python3
"""Check optional data-provider dependencies for research runs."""

from __future__ import annotations

import argparse
import importlib.util
import json


def check_modules(module_names: list[str]) -> dict[str, object]:
    modules = {
        name: {"available": importlib.util.find_spec(name) is not None}
        for name in module_names
    }
    missing = [name for name, info in modules.items() if not info["available"]]
    return {
        "status": "FAIL" if missing else "PASS",
        "modules": modules,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check optional data dependencies.")
    parser.add_argument("--module", action="append", required=True)
    args = parser.parse_args()

    payload = check_modules(args.module)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
