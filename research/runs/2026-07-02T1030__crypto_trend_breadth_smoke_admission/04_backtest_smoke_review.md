# Backtest Smoke Review - Crypto Trend Breadth Top2

Verdict: `FAIL_FORMAL_BACKTEST`

Smoke status: `PASS_WITH_WARNINGS`

## Backtest Reviewed

No formal crypto backtest is reviewed in this document. The planned run is a
synthetic smoke artifact only.

## Artifact Gate

Formal backtest validation requires:

- `config_snapshot.yaml`
- `orders.csv`
- `trades.csv`
- `equity.csv`
- `events.jsonl`
- `report.md`

The parent crypto admission artifacts directory lacked these files. Today's
run generated them only for the synthetic smoke path.

## Synthetic Smoke Result

Command:

```bash
/tmp/quant-research-venv/bin/python scripts/run_backtest.py \
  --strategy research/runs/2026-07-02T1030__crypto_trend_breadth_smoke_admission/artifacts/synthetic_smoke_input/strategy.yaml \
  --data-root research/runs/2026-07-02T1030__crypto_trend_breadth_smoke_admission/artifacts/synthetic_smoke_input \
  --out research/runs/2026-07-02T1030__crypto_trend_breadth_smoke_admission/artifacts/synthetic_smoke_result \
  --initial-cash 1000
```

Artifact inspector:

```text
status: PASS_WITH_WARNINGS
warning: equity.csv has fewer than 20 rows
orders rows: 2
trades rows: 2
equity rows: 3
events rows: 16
```

Report facts:

- `not_trading_permission: true`
- `dataset_manifest_copied: true`
- benchmarks present: `cash_usdt`, `hold_btc`, `hold_eth`, `hold_sol`,
  `equal_weight_crypto`
- total fee: `1.0`
- estimated slippage cost: `2.0`

The return and drawdown in this synthetic report are not strategy evidence.

## Blocking Issues For Formal Backtest

- No audited real crypto dataset.
- No formal baseline over sufficient history.
- No benchmark and ablation package over real data.
- No sample split, rolling window, regime, or cost stress package.
- No risk review based on real backtest artifacts.

## Warnings

- Synthetic smoke output must not be used for performance interpretation.
- A complete artifact six-pack is necessary but not sufficient for backtest
  credibility.
- The synthetic full-allocation target plus fees produced a small negative cash
  balance after fills. Formal research must add a fee-reserve or cost-aware
  sizing decision before risk review.

## Required Next Checks

1. Keep formal verdict as `FAIL` until real data audit passes.
2. Resolve or explicitly gate fee-reserve/cash-buffer behavior.
3. After real data audit, run baseline, mild/stress costs, benchmarks,
   ablations, sample splits, and risk review.
