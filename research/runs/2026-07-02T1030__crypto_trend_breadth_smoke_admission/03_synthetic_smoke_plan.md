# Synthetic Smoke Plan - Crypto Trend Breadth Top2

Status: `SMOKE_ONLY`

## Purpose

Validate the research execution chain using synthetic data:

- strategy import through `strategies.crypto_trend_breadth:CryptoTrendBreadthTop2`;
- 7x24 primary `4h` timeline;
- daily trend history visible at 4h decisions;
- next-bar target execution;
- bps fee and slippage reporting;
- manifest copy and benchmark reporting.

## Input Artifacts

- `artifacts/synthetic_smoke_input/strategy.yaml`
- `artifacts/synthetic_smoke_input/dataset_manifest.yaml`
- `artifacts/synthetic_smoke_input/bars_1d.csv`
- `artifacts/synthetic_smoke_input/bars_4h.csv`
- `artifacts/synthetic_smoke_input/instruments.csv`

The data source is `synthetic_strategy_contract_fixture`. It is intentionally
tiny and artificial.

## Expected Output Artifacts

- `artifacts/synthetic_smoke_result/config_snapshot.yaml`
- `artifacts/synthetic_smoke_result/orders.csv`
- `artifacts/synthetic_smoke_result/trades.csv`
- `artifacts/synthetic_smoke_result/equity.csv`
- `artifacts/synthetic_smoke_result/events.jsonl`
- `artifacts/synthetic_smoke_result/report.md`
- `artifacts/synthetic_smoke_result/report.json`
- `artifacts/synthetic_smoke_result/dataset_manifest.yaml`

## Explicit Non-Goals

- No return or drawdown conclusion.
- No edge claim.
- No parameter tuning.
- No formal backtest validation.
- No paper/live plan.

## Smoke Pass Conditions

- CLI exits 0.
- Standard six-pack artifact files exist.
- `report.json` marks `not_trading_permission: true`.
- `dataset_manifest.yaml` is copied into the output.
- Artifact inspector passes completeness checks.

## Formal Gate Boundary

Synthetic smoke can only move the framework gate from "not runnable" to
"runnable on synthetic fixture." It cannot move data audit, formal backtest
validation, risk promotion, paper observation, or paper/live gate.
