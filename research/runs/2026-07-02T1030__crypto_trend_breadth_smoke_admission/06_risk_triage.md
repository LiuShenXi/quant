# Risk Triage - Crypto Trend Breadth Top2 Smoke Admission

Decision: `APPROVE_WITH_LIMITS`

Scope: research-only synthetic smoke for `crypto_trend_breadth_top2_v1`.

This is not paper approval, live approval, exchange approval, broker approval,
QMT approval, or real-money authorization.

## Scope

- Account: synthetic research account only.
- Initial capital: `1000` USDT in synthetic smoke.
- Instruments: synthetic BTC, ETH, SOL spot proxies.
- Mode: `SMOKE_ONLY`.

## Blocking Risk Issues For Paper/Live

- No audited real crypto dataset.
- No formal backtest artifact over real data.
- No formal risk review for paper.
- No broker, exchange, reconciliation, alerting, or incident process.
- No M3b evidence.

## Smoke Warnings

- The 60% plus 40% target fully allocates capital before fees.
- The synthetic smoke generated a small negative cash balance after fees:
  `cash_after: -1.0`.
- This does not block synthetic smoke, but it blocks any formal risk promotion
  until a cost-aware sizing or cash-buffer policy is explicit and tested.

## Limit Changes Required Before Formal Review

- Define whether target weights reserve fee/slippage cash or whether the engine
  rejects orders that would overdraw cash after fees.
- Keep max gross exposure at or below 100% spot notional.
- Keep leverage, margin, futures, options, and shorts disallowed.
- Keep portfolio stop and cooldown outside strategy logic.

## Evidence Reviewed

- `artifacts/synthetic_smoke_result/events.jsonl`
- `artifacts/synthetic_smoke_result/report.json`
- `artifacts/synthetic_smoke_input/strategy.yaml`
- `src/quant/risk/portfolio_stop.py`
- `src/quant/backtest/engine.py`
- `.agents/skills/risk-governor/references/live-risk-gates.md`

## Human Signoff Needed

No human capital authorization is needed for synthetic smoke.

Human signoff is required before any paper observation, exchange connectivity,
credentials, live-adjacent work, capital change, or real-money discussion.
