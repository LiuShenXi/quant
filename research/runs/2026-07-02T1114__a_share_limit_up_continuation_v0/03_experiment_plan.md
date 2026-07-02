# Experiment Plan - A-Share Limit-Up Continuation v0

Status: DESIGN_ONLY
Run ID: `2026-07-02T1114__a_share_limit_up_continuation_v0`
Strategy ID: `a_share_limit_up_continuation_v0`
Mode: research-only

## Purpose

Define the smallest experiment set that can validate or falsify whether A-share limit-up events have a short-horizon continuation effect after realistic data, execution, cost, and risk constraints.

This plan does not authorize backtesting yet. It defines what a later auditable backtest would need to prove or disprove.

## Data Inputs

- Dataset paths: blocked until data-source selection.
- Manifest paths: blocked until data-source selection.
- Calendar: A-share exchange trading calendar with suspensions and holidays.
- Adjustment: raw prices for event and price-limit detection; adjusted series only for return normalization where appropriate.
- Known data warnings: no audited dataset; no approved intraday or order-book data; no survivorship-bias policy.

## Baseline

Primary baseline rule:

- Identify stocks that hit limit-up on day `t`.
- Do not assume same-day entry on day `t`.
- Measure next-session and 1-3 session forward return distributions from predefined execution points, such as next open, next VWAP proxy if available, or next close.
- Exclude ST, suspended, newly listed, delisting-risk, and unhandled special-rule instruments until the data audit approves explicit handling.

Benchmark set:

- All A-share equal-weight next-session return.
- High-turnover or high-volume momentum baseline.
- Sector-matched return baseline.
- Limit-up event without filters.

Cost model:

- Fees and taxes documented before running.
- Slippage stress levels documented before running.
- Failed-entry and failed-exit stress documented before running.

Execution assumptions:

- Daily continuation baseline uses next-session execution only.
- Same-day board-capture experiment is blocked until intraday or order-book data exists.
- T+1, price-limit lockup, suspension, and failed-exit cases must be modeled conservatively.

Risk assumptions:

- Single-name exposure and event-cluster exposure are capped outside strategy logic in later risk review.
- Drawdown, tail loss, and halt/freeze rules must be reviewed by `risk-governor` before paper discussion.

## Experiment Matrix

| Experiment | Purpose | Variables fixed before run | Metrics | Expected evidence | Status |
| --- | --- | --- | --- | --- | --- |
| event_baseline | Test raw next-session continuation after a limit-up event | universe exclusions, event definition, forward windows, cost model | event count, mean/median return, win rate, tail loss, drawdown proxy | whether unconditional limit-up continuation exists | DESIGN_ONLY |
| quality_filter | Test whether board quality and market context matter | filter list, thresholds or quantile buckets, no post-hoc tuning | distribution lift, event count, regime stability | whether any filter is explanatory rather than curve-fit | DESIGN_ONLY |
| cost_stress | Check fee, tax, and slippage fragility | cost levels, slippage levels, failed-entry/exit penalties | cost-adjusted return, break-even slippage, worst clusters | whether apparent edge survives realistic trading friction | DESIGN_ONLY |
| sample_split | Check time-period fragility | train/test or chronological split definitions | in-sample vs out-of-sample metrics | whether results depend on one window | DESIGN_ONLY |
| regime_split | Check bull, bear, sideways, high-volatility, mania, and unwind periods | regime labels and definitions | per-regime return, event count, worst regime | whether the thesis is actually a regime bet | DESIGN_ONLY |
| benchmark_ablation | Check whether a simpler rule explains returns | benchmark list and matching logic | excess return vs benchmark, risk-adjusted difference | whether limit-up logic adds value beyond momentum/liquidity | DESIGN_ONLY |
| board_capture_gate | Decide whether same-day board capture is researchable | intraday/order-book data availability and fill rules | fill rate, skipped trades, adverse selection, failed exits | whether daily data must remain the boundary | BLOCKED_PENDING_DATA |

## Metrics

- Event count and eligible universe count.
- Mean, median, quantiles, and tail forward return.
- Win rate, payoff ratio, and loss clustering.
- Maximum adverse excursion where intraday data exists.
- Turnover and estimated cost paid.
- Failed-entry and failed-exit sensitivity.
- Regime contribution and worst regime.
- Drawdown proxy and tail-event clusters.
- Benchmark-relative return distribution.

## Pass Conditions

- Data audit is `PASS` or documented `PASS_WITH_WARNINGS`.
- Baseline uses costs and execution assumptions declared before the run.
- Event definitions and universe exclusions are fixed before seeing performance results.
- Results survive cost stress, sample split, and regime split.
- Results are not dominated by a tiny number of events or one market mania period.
- Board-capture claims are made only if intraday or order-book evidence supports executable fills.
- Risk behavior remains reviewable outside strategy logic.

## Falsification Rules

- Stop or redesign if daily data is used to claim same-day limit-up buyability.
- Stop or redesign if results require post-hoc thresholds selected after seeing returns.
- Stop or redesign if realistic costs, failed entry, or failed exit destroy the thesis.
- Stop or redesign if results are concentrated in one date window, sector mania, or a few extreme events.
- Stop or redesign if drawdown, tail loss, liquidity lockup, or event clustering fails independent risk review.

## Reproducibility Notes

Commands to run: blocked until data-source selection.
Output artifact path: blocked until data-source selection.
Config snapshot path: blocked until data-source selection.
Random seed or deterministic setting: deterministic event definitions required.
Review owner: `backtest-validator` after artifacts exist.
