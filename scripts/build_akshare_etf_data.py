from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    from quant.data.akshare_etf import fetch_etf_dataset, write_dataset

    parser = argparse.ArgumentParser(description="Build a real A-share ETF daily data_root.")
    parser.add_argument("--symbol", default="510300.SH")
    parser.add_argument("--name", default="沪深300ETF")
    parser.add_argument("--start-date", required=True, help="YYYYMMDD")
    parser.add_argument("--end-date", required=True, help="YYYYMMDD")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    dataset = fetch_etf_dataset(
        symbol=args.symbol,
        name=args.name,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    write_dataset(dataset, args.out)
    print(f"wrote real ETF data_root: {args.out}")
    print(f"bars: {len(dataset['bars_1d'])}")
    print(f"calendar days: {len(dataset['trade_calendar'])}")


if __name__ == "__main__":
    main()
