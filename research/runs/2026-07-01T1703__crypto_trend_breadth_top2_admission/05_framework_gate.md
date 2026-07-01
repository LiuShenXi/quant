# Framework Gate - Crypto Trend Breadth Top2 Admission

Status: `FRAMEWORK_GAP_IDENTIFIED`

This document separates existing reusable engine capability from missing generic framework capability. It is not a request to customize the engine for one strategy.

## Existing Reusable Capabilities

The current repository already provides:

- Strategy contract with `on_bar`, `ctx.history`, `ctx.set_target`, positions, account, state.
- Multi-symbol daily backtest loop.
- Target-to-order conversion.
- Order, trade, equity, and event artifacts.
- Basic cost model.
- Risk checks for symbol whitelist, single-order notional, position value, gross exposure, frequency, and daily loss.
- Artifact inspection and benchmark reporting scripts.

These capabilities are useful foundations for future crypto research.

## Current Blocking Gaps For Formal Crypto Backtest

The current engine cannot yet produce a formal, credible `crypto_trend_breadth_top2_v1` backtest artifact because:

- Strategy config currently restricts `freq` to `1d`.
- `DataService.history()` rejects non-`1d` frequencies.
- Backtest sessions are grouped by date and use an A-share style 09:31 open.
- Risk checks include A-share continuous auction session validation.
- Current data contracts expect A-share/ETF style tables and adjustment factors.
- Portfolio account currency is fixed to CNY in the current portfolio output.
- The cost model is commission/min-fee oriented and does not separately model bps fee plus bps slippage.
- Portfolio-level trailing drawdown stop and re-entry gate are not reusable generic risk components yet.
- Multi-timeframe daily trend plus 4-hour execution needs explicit anti-leakage support.
- Current `report.md` output is too thin for this strategy family: final value alone is insufficient; formal review needs CAGR, Calmar, volatility, turnover, time in cash, time by symbol, costs, slippage, ablations, and regime contribution.
- Current `events.jsonl` is derived from orders/trades and does not yet represent a full append-only research event journal covering rebalance decisions, risk stops, cash transitions, re-entry events, and engine state changes.

## Non-Blocking Research Work

Business research can continue now:

- Thesis refinement.
- Data source selection.
- Data audit checklist design.
- Experiment matrix design.
- Benchmark definitions.
- Framework gate definition.
- CIO decision packaging.

## Blocking Until Framework Gate Passes

The following must wait:

- Formal backtest credibility claims.
- `backtest-validator` PASS or PASS_WITH_WARNINGS.
- Risk promotion review for paper.
- Paper observation plan.
- Any exchange, broker, live, QMT, or real-money step.
- Any claim that risk-stop or re-entry behavior has been independently audited.

## Generic Framework Requirement Reminder

Any technical implementation must provide generic configurable capabilities. It must not hard-code:

- `crypto_trend_breadth_top2_v1`
- BTC/ETH/SOL
- stablecoin symbol
- 4-hour or daily frequency
- 50-day EMA or 20-bar ranking
- 60/40 weights
- 20% stop
- 5-day cooldown
- 35% review limit

The strategy may be used as an acceptance fixture, not as an engine dependency.
