# Thesis Update - ETF Regime Rotation v1

Status: `THESIS_UPDATE`

## Hypothesis

ETF regime rotation between `510300.SH` and `510500.SH` may offer
drawdown-controlled participation by holding the stronger eligible ETF only
when it is above a trend baseline.

The thesis should no longer be framed as proven absolute-return alpha. Existing
same-window evidence shows lower drawdown, but also lower absolute return than
simple long-only ETF baselines.

## Evidence

- Existing strategy code and config are preserved under
  `research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab`.
- Existing backtest artifacts are complete for the inspected run:
  `orders.csv`, `trades.csv`, `equity.csv`, `events.jsonl`,
  `report.md`, and `config_snapshot.yaml`.
- Current deterministic check found:
  - bars rows: 518
  - symbols: `510300.SH`, `510500.SH`
  - bar range: `2025-06-03T15:00:00+08:00` to
    `2026-06-25T15:00:00+08:00`
  - orders: 25
  - trades: 25
  - equity rows: 518
  - event lines: 50
  - initial value: 100000.00
  - final value: 120098.30
- Existing robustness probe from `runs/cio/2026-06-27` found:
  - ETF rotation return: 20.10%, max drawdown: -6.49%
  - `510300.SH` buy-and-hold return: 27.57%, max drawdown: -9.94%
  - `510500.SH` buy-and-hold return: 59.30%, max drawdown: -14.02%
- Current normalized equal-weight benchmark report found:
  - equal-weight return: 43.4368%, max drawdown: -10.7071%
  - method: close-to-close normalized buy-and-hold
- Current sample-split report found:
  - first half strategy return: 1.3941%, max drawdown: -5.7348%
  - first half equal-weight return: 23.6013%
  - second half strategy return: 18.9313%, max drawdown: -6.4892%
  - second half equal-weight return: 16.4916%

## Assumptions

- The AKShare/Sina ETF daily-bar dataset is acceptable for research only after
  keeping its calendar/bar mismatch warning visible.
- Daily-bar execution semantics are close enough for initial research, but must
  be documented before any paper discussion.
- The lower-drawdown tradeoff may be valuable only if it remains stable across
  longer history and cost assumptions.

## Falsifiers

- Longer-history tests show no durable drawdown benefit.
- Cost or delay sensitivity removes the observed benefit.
- Sample splits show the result comes from one favorable regime.
- Universe choice cannot be justified without hindsight.
- Risk review finds that independent `quant.risk` limits cannot contain the
  strategy without changing the thesis.

## Data Needed

- Longer reproducible ETF dataset.
- Dataset build command and log for the combined ETF rotation dataset.
- File hashes for all data and backtest artifacts.
- Benchmark series for single ETF holds, equal-weight hold, and cash/risk-off
  baselines.

## Validation Path

1. Preserve current evidence and hashes.
2. Run longer-history data build if provider coverage allows it.
3. Run benchmark, cost, delay, and sample-split robustness tests.
4. Re-run data audit and backtest validation on the extended artifact package.
5. Route to risk-governor only if robustness supports continued research.

## Next Decision

`HOLD_FOR_ROBUSTNESS`. Continue evidence building with longer-history
robustness, do not route to paper.
