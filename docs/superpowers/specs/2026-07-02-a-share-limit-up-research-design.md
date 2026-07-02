# A-Share Limit-Up Continuation Research Design

Date: 2026-07-02
Owner: Codex research
Mode: research-only

## Scope

Create a research-only package for `a_share_limit_up_continuation_v0`, a short-horizon A-share individual-stock thesis about whether limit-up events have auditable next-session continuation value.

This design does not create strategy code, backtest code, paper trading configuration, QMT integration, broker connectivity, live overlays, credentials, or real orders.

## Recommended Approach

Use a narrow research package under `research/runs/2026-07-02T1114__a_share_limit_up_continuation_v0/`.

The package should include:

- `00_brief.md` for CIO scope and default safe action.
- `01_thesis.md` for the falsifiable strategy thesis.
- `02_data_requirements.md` for required A-share data and known gaps.
- `03_experiment_plan.md` for event-study and conservative execution tests.
- `05_cio_decision_package.md` for the research-only decision.
- `run.yaml` for machine-readable run metadata.

Update cross-run registries so the candidate is discoverable.

## Boundaries

The main distinction is between two research questions:

1. Post-limit-up continuation: whether stocks that hit limit-up show positive next-session or 1-3 day return distribution after costs.
2. Limit-up board capture: whether a simulated order can realistically buy during or near the limit-up event.

The first question may be studied with daily bars plus robust limit-price fields, although execution assumptions still need stress tests. The second question cannot be validated with daily bars alone; it needs intraday, order-book, or equivalent queue/auction evidence.

## Data Requirements

Minimum research data:

- A-share instruments with exchange, board, listing date, delisting status, ST status, suspension status, and corporate action handling.
- Trading calendar with sessions, non-trading days, and exchange-specific trading status.
- Daily OHLCV, turnover, amount, limit-up price, limit-down price, and adjusted/unadjusted close.
- Board-specific price-limit rules and IPO or special-condition exceptions, sourced from exchange rules or an auditable vendor.

Board-capture data:

- Minute bars at minimum.
- Preferably tick, auction, order-book, or queue indicators that can distinguish "hit limit-up" from "buyable at limit-up".

## Experiments

Start with design-only experiments:

- Event baseline: identify limit-up events and measure next-open, next-close, and 1-3 session forward returns.
- Filter tests: split by board quality, volume, turnover, market breadth, sector breadth, prior trend, and opening gap.
- Cost stress: apply fees, tax, slippage, failed-entry assumptions, and failed-exit assumptions.
- Regime split: bull, bear, sideways, high-volatility, and limit-up mania or unwind periods.
- Benchmark ablation: compare with simpler momentum or high-volume baselines.

## Tests And Review

No code is changed in this design. Verification is document-level:

- Files exist in the research run directory.
- Registries include the new candidate and evidence package.
- Thesis status remains `THESIS_DRAFT`.
- CIO decision remains `RESEARCH_ONLY`.

Before any backtest or paper discussion, the candidate must pass thesis, data audit, backtest validation, and risk review in order.
