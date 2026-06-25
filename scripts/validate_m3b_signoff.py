from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from quant.live.signoff import SignoffValidationError, validate_m3b_signoff  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the operator-authored M3b signoff artifact before M4a/QMT.",
    )
    parser.add_argument("signoff", type=Path, help="Path to m3b_signoff.yaml")
    args = parser.parse_args(argv)

    try:
        validate_m3b_signoff(args.signoff)
    except (OSError, SignoffValidationError, yaml.YAMLError) as error:
        print(f"M3b signoff rejected: {error}", file=sys.stderr)
        print("M4a remains blocked.", file=sys.stderr)
        return 1

    print(f"M3b signoff validated: {args.signoff}")
    print("M4a may start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
