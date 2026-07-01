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
        for event in result.events:
            file.write(json.dumps(_serializable(event), ensure_ascii=False) + "\n")
    final_value = result.equity[-1]["total_value"] if result.equity else 0
    (output_dir / "report.md").write_text(
        f"# Backtest Report\n\nFinal value: {final_value}\n",
        encoding="utf-8",
    )


def _serializable(value) -> dict[str, object]:
    data = asdict(value)
    return {key: _json_value(item) for key, item in data.items()}


def _json_value(value):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value
