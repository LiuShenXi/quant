from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    from quant.core.config import load_strategy_config
    from quant.live.config import load_global_risk_config, load_paper_config
    from quant.live.engine import PaperEngine

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--risk", default="config/risk/global.yaml")
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--disconnect-drill", action="store_true")
    parser.add_argument("--disconnect-reason", default="disconnect drill")
    args = parser.parse_args()

    result = PaperEngine(
        load_strategy_config(Path(args.strategy)),
        load_paper_config(Path(args.paper)),
        load_global_risk_config(Path(args.risk)),
    ).run_replay(
        max_bars=args.max_bars,
        disconnect_drill=args.disconnect_drill,
        disconnect_reason=args.disconnect_reason,
    )
    print(f"paper events: {result.events_path}")
    print(f"paper store: {result.store_path}")
    print(f"final state: {result.final_state}")
    for drill_event in result.drill_events:
        print(f"disconnect drill: {drill_event}")


if __name__ == "__main__":
    main()
