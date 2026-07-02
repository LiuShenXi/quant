from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_backtest.py"


def test_run_backtest_cli_passes_data_root_to_research_report(tmp_path: Path) -> None:
    data_root = _write_cli_dataset(tmp_path / "data")
    strategy_path = _write_cli_strategy(tmp_path / "strategy.yaml")
    output_dir = tmp_path / "smoke"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--strategy",
            str(strategy_path),
            "--data-root",
            str(data_root),
            "--out",
            str(output_dir),
            "--initial-cash",
            "1000",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))

    assert report["dataset_manifest_copied"] is True
    assert (output_dir / "dataset_manifest.yaml").read_text(
        encoding="utf-8"
    ) == (data_root / "dataset_manifest.yaml").read_text(encoding="utf-8")
    assert report["benchmarks"]["hold_aaa"]["type"] == "single_asset_buy_hold"


def _write_cli_strategy(path: Path) -> Path:
    path.write_text(
        """
id: cli_manifest_smoke
class: strategies.dual_ma:DualMA
version: 1.0.0
universe:
  - AAA
frequencies:
  primary: 1d
  history:
    - 1d
calendar: continuous_24x7
account:
  currency: USD
  settlement: t0
  allow_fractional: true
params:
  symbol: AAA
  fast: 1
  slow: 1
  target_qty: 1
risk:
  max_order_value:
    value: 1000
    unit: quote_currency
    currency: USD
  max_position_value:
    value: 1000
    unit: quote_currency
    currency: USD
  max_gross_exposure_pct: 1.0
costs:
  model: bps
  preset: cli_smoke
  fee_bps: 1
  slippage_bps: 1
benchmarks:
  - id: hold_aaa
    type: single_asset_buy_hold
    symbol: AAA
runtime_mode: backtest
""",
        encoding="utf-8",
    )
    return path


def _write_cli_dataset(data_root: Path) -> Path:
    data_root.mkdir()
    (data_root / "bars_1d.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,pre_close,limit_up,limit_down,suspended,data_status,source,updated_at",
                "AAA,2026-01-01T00:00:00+00:00,10,11,9,10,1000,10000,10,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "AAA,2026-01-02T00:00:00+00:00,11,12,10,11,1000,11000,10,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "instruments.csv").write_text(
        "\n".join(
            [
                "symbol,name,type,exchange,list_date,delist_date,lot_size,qty_step,tick_size,t_plus,status,allow_fractional",
                "AAA,AAA,synthetic,TEST,2026-01-01,,0.001,0.001,0.01,0,active,true",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "dataset_manifest.yaml").write_text(
        """
dataset_id: cli_manifest_smoke
source: synthetic_cli_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2026-01-01T00:00:00Z"
  end: "2026-01-02T00:00:00Z"
symbols:
  - symbol: AAA
    type: synthetic
    exchange: TEST
    active_from: "2026-01-01T00:00:00Z"
    active_to: null
    qty_step: 0.001
    lot_size: 0.001
    t_plus: 0
frequencies:
  - freq: 1d
    file: bars_1d.csv
    expected_interval: P1D
    coverage:
      start: "2026-01-01T00:00:00Z"
      end: "2026-01-02T00:00:00Z"
    construction: synthetic_source
""",
        encoding="utf-8",
    )
    return data_root
