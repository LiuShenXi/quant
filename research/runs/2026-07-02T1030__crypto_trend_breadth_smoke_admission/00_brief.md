# Research Brief - Crypto Trend Breadth Top2 Smoke Admission

Run ID: `2026-07-02T1030__crypto_trend_breadth_smoke_admission`
Created: 2026-07-02 10:30 +08:00
Status: research-only
Strategy ID: `crypto_trend_breadth_top2_v1`
Parent run: `research/runs/2026-07-01T1703__crypto_trend_breadth_top2_admission`

## Purpose

Continue yesterday's crypto research after generic engine capabilities were
implemented. Today's goal is not to prove strategy edge. Today's goal is to
turn the thesis and framework gate into a reproducible `SMOKE_ONLY` research
package:

1. Confirm the strategy can be imported through the strategy contract.
2. Run a synthetic, tiny, 7x24, 4h plus 1d smoke artifact.
3. Preserve the formal data-audit and formal backtest blockers.
4. Define the next real-data research task.

This package is not investment advice, investment recommendation, paper
approval, live approval, exchange connectivity approval, broker approval, or
real-money trading permission.

## Today's Mainline Decision

CIO Decision: `SMOKE_ONLY_RESEARCH_CONTINUE`

The research mainline may continue from design-only admission to synthetic
artifact smoke. Formal crypto data audit remains `FAIL`; formal crypto backtest
validation remains `FAIL`.

## Evidence Produced Today

- Added a contract-level implementation of
  `strategies.crypto_trend_breadth:CryptoTrendBreadthTop2`.
- Added deterministic tests for the strategy smoke and CLI report manifest
  propagation.
- Added a run-local synthetic smoke input dataset and strategy config.
- Generated a synthetic smoke artifact with the standard backtest six-pack.

## Default Safe Action

Keep `crypto_trend_breadth_top2_v1` research-only. Do not paper, live, connect
exchanges, connect brokers, use credentials, increase capital, or generate real
orders.
