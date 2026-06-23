import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

import pandas as pd
import yaml

from quant.backtest.engine import BacktestResult
from quant.core.config import StrategyConfig


def write_result(result: BacktestResult, output_dir: Path, config: StrategyConfig) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "config_snapshot.yaml").open("w", encoding="utf-8") as file:
        yaml.safe_dump(config.model_dump(mode="json", by_alias=True), file, allow_unicode=True)
    pd.DataFrame([_serializable(order) for order in result.orders]).to_csv(
        output_dir / "orders.csv",
        index=False,
    )
    pd.DataFrame([_serializable(trade) for trade in result.trades]).to_csv(
        output_dir / "trades.csv",
        index=False,
    )
    pd.DataFrame(result.equity).to_csv(output_dir / "equity.csv", index=False)
    with (output_dir / "events.jsonl").open("w", encoding="utf-8") as file:
        for order in result.orders:
            file.write(
                json.dumps(
                    {"type": "order", "payload": _serializable(order)},
                    ensure_ascii=False,
                )
                + "\n"
            )
        for trade in result.trades:
            file.write(
                json.dumps(
                    {"type": "trade", "payload": _serializable(trade)},
                    ensure_ascii=False,
                )
                + "\n"
            )
    final_value = result.equity[-1]["total_value"] if result.equity else 0
    (output_dir / "report.md").write_text(
        f"# Backtest Report\n\nFinal value: {final_value}\n",
        encoding="utf-8",
    )


def _serializable(value) -> dict[str, object]:
    data = asdict(value)
    for key, item in data.items():
        if isinstance(item, Enum):
            data[key] = item.value
        elif hasattr(item, "isoformat"):
            data[key] = item.isoformat()
    return data
