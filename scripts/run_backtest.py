import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from quant.backtest.engine import BacktestEngine
    from quant.backtest.results import write_result
    from quant.core.config import load_strategy_config
    from quant.data.service import DataService

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--data-root", default="data_sample")
    parser.add_argument("--out", required=True)
    parser.add_argument("--initial-cash", type=float, default=100_000)
    args = parser.parse_args()

    config = load_strategy_config(Path(args.strategy))
    data = DataService(Path(args.data_root))
    result = BacktestEngine(config=config, data=data, initial_cash=args.initial_cash).run()
    write_result(result, output_dir=Path(args.out), config=config)


if __name__ == "__main__":
    main()
