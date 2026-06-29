# Risk Triage - ETF Regime Rotation v1

Decision: `APPROVE_FOR_REVIEW`

Scope:

Research-only risk triage for `etf_regime_rotation_v1`, not paper/live
admission.

## Blocking Risk Issues

None for continuing research review.

For paper/live-adjacent progression, the following remain blocking:

- no robustness package proving the lower-drawdown tradeoff is durable
- no formal paper observation plan for this strategy
- no M3b signoff package
- no paper/live gatekeeper review
- no human risk authorization

## Limit Changes Required

None for research-only continuation.

Do not loosen risk limits to make this strategy look better.

## Evidence Reviewed

- Strategy config snapshot:
  - `max_order_value: 100000`
  - `max_position_value: 100000`
  - `max_gross_exposure_pct: 0.95`
  - `target_exposure_pct: 0.8`
- Global risk config:
  - `max_order_value: 200000`
  - `max_position_value_per_symbol: 500000`
  - `max_gross_exposure_pct: 0.95`
  - daily loss freeze: 2%
  - daily loss halt: 4%
- `src/quant/risk/pipeline.py`
- `src/quant/backtest/engine.py`

## Human Signoff Needed

No human signoff is needed to continue research evidence building.

Human authorization is required before any capital, paper/live-adjacent stage,
M4/QMT, broker, or real-money boundary change.

