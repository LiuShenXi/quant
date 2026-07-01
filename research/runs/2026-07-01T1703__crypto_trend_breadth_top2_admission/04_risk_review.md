# Risk Review - Crypto Trend Breadth Top2 Admission

Decision: `APPROVE_WITH_LIMITS`

Scope: research-only admission design for `crypto_trend_breadth_top2_v1`.

This is not paper approval, live approval, exchange approval, broker approval, QMT approval, or real-money authorization.

## Scope

- Account: hypothetical research account only.
- Initial capital assumption: CNY 50,000 equivalent.
- Strategy: `crypto_trend_breadth_top2_v1`.
- Mode: research-only.
- Instruments: BTC spot, ETH spot, SOL spot, stablecoin cash.
- Requested decision: whether business research may continue before engine implementation finishes.

## Blocking Risk Issues

Blocking for paper/live/promotion:

- No audited dataset.
- No formal backtest artifact.
- No independent implementation of portfolio-level drawdown stop in reusable risk framework.
- No quote-currency/stablecoin accounting audit.
- No exchange, broker, gateway, reconciliation, alerting, or incident process for crypto.
- No M3b evidence and no paper/live gate review.

Not blocking for research-only:

- Thesis drafting.
- Data source screening.
- Experiment design.
- Framework gate definition.

## Limit Changes Required

For future formal review, limits must be explicit and independently enforceable:

- Max gross exposure: 100% spot notional.
- Max single risky asset target: 60% under normal Top2 allocation.
- Defensive allocation: 100% stablecoin cash.
- Portfolio trailing stop: 20% active-cycle drawdown.
- Research hard red line: 35% full-equity max drawdown.
- Rebalance cap: at most once per UTC day.
- Leverage, margin, futures, options, shorts: not allowed in v1.

## Evidence Reviewed

- `docs/superpowers/specs/2026-07-01-crypto-trend-breadth-top2-design.md`
- `AGENTS.md`
- `docs/agents/risk-authorization-hooks.md`
- `src/quant/risk/pipeline.py`
- `src/quant/backtest/engine.py`

## Human Signoff Needed

No human capital authorization is needed for research-only documentation and data screening.

Human signoff would be required before:

- Any paper observation.
- Any exchange or broker integration.
- Any real credentials.
- Any live/paper risk boundary change.
- Any capital expansion or真钱 discussion.

## Required Next Checks

- Data audit before any backtest validation.
- Backtest artifact review before risk promotion review.
- Independent risk component review before paper discussion.

