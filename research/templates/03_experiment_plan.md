# Experiment Plan

Status: DESIGN_ONLY
Run ID:
Strategy ID:
Mode: research-only

## Purpose

Define the smallest experiment set that can validate or falsify the thesis
without optimizing parameters to make the strategy look better.

## Data Inputs

- Dataset paths:
- Manifest paths:
- Calendar:
- Adjustment:
- Known data warnings:

## Baseline

Primary baseline rule:
Benchmark set:
Cost model:
Execution assumptions:
Risk assumptions:

## Experiment Matrix

| Experiment | Purpose | Variables fixed before run | Metrics | Expected evidence | Status |
| --- | --- | --- | --- | --- | --- |
| baseline | Test the stated thesis with default assumptions |  |  |  | DESIGN_ONLY |
| cost_stress | Check fee and slippage fragility |  |  |  | DESIGN_ONLY |
| sample_split | Check time-period fragility |  |  |  | DESIGN_ONLY |
| benchmark_ablation | Check whether added complexity matters |  |  |  | DESIGN_ONLY |

## Metrics

- Total return.
- CAGR or annualized return where appropriate.
- Max drawdown.
- Calmar ratio or drawdown-adjusted return.
- Volatility.
- Turnover.
- Number of trades or rebalances.
- Cost paid.
- Time in cash or risk-off state where applicable.
- Best and worst regime contribution.

## Pass Conditions

- Data audit is `PASS` or documented `PASS_WITH_WARNINGS`.
- Baseline uses costs and execution assumptions declared before the run.
- Results are not dominated by a manually selected date window or a tiny number
  of trades.
- Benchmarks and ablations do not invalidate the added strategy complexity.
- Risk behavior remains reviewable outside the strategy logic.

## Falsification Rules

- Stop or redesign if the thesis only works under changed parameters selected
  after viewing results.
- Stop or redesign if results require future data, same-bar execution, or
  unaudited data.
- Stop or redesign if realistic costs destroy the thesis.
- Stop or redesign if a simpler benchmark dominates with similar or lower risk.

## Reproducibility Notes

Commands to run:
Output artifact path:
Config snapshot path:
Random seed or deterministic setting:
Review owner:
