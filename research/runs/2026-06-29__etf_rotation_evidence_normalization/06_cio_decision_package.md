# CIO Decision Package - 2026-06-29

CIO Decision: `HOLD_FOR_ROBUSTNESS`

## Strategy Opportunity

`etf_regime_rotation_v1` remains the best first research candidate because it
has existing strategy code, config, data, backtest artifacts, and a prior CIO
package. Its value proposition should be narrowed to drawdown-controlled ETF
participation rather than proven alpha.

## Recommended Next Action

Run the next robustness loop before any paper or risk-admission discussion:

1. restore data dependency access, then build or version a longer reproducible ETF dataset
2. generate full benchmark comparisons
3. run cost, delay, and sample-split sensitivity
4. produce a complete artifact inspection/report package

## Candidate Strategies

| Strategy | Decision |
| --- | --- |
| `etf_regime_rotation_v1` | Continue research, hold for robustness |
| DualMA 510300 | Keep as operational baseline only |
| DualMA 510500 | Keep in candidate pool, no promotion |
| Broader ETF momentum basket | Defer until data governance is stronger |

## Evidence Reviewed

- `research/imported/usage_records/2026-06-26__quant_usage_record`
- `research/runs/cio/2026-06-27`
- current data file statistics and hashes
- current backtest artifact statistics and hashes
- skill-level artifact inspection results
- `config/risk/global.yaml`
- `config/costs/cn_etf.yaml`
- `src/quant/data/service.py`
- `src/quant/risk/pipeline.py`
- `src/quant/backtest/engine.py`

## Experiments To Run

- longer-history data build after `akshare` dependency is available
- same-window benchmark comparison on extended data
- cost sensitivity
- delayed-execution sensitivity
- sample split by market regime
- parameter fragility review

## Sub-Agent Routing

```text
Quant CIO Orchestrator: complete today's classification and decision package
Strategy Thesis Tracker: THESIS_UPDATE
Data Audit Reviewer: PASS_WITH_WARNINGS for current research data
Backtest Validator: PASS_WITH_WARNINGS for preserving current artifact
Risk Governor: APPROVE_FOR_REVIEW for research-only continuation
Paper/Live Gatekeeper: not applicable; M4/QMT/live remains blocked
```

## Improvement Proposal

Keep the strategy in research while improving evidence quality. Repo-level
artifact completeness, core metrics, current-window benchmark, and current-window
sample-split reports now exist. The remaining engineering improvement is a
longer-history report layer.

## Risk Authorization Needed

None for research-only continuation.

Human authorization and gate review are required for paper/live-adjacent
progression, capital changes, M4/QMT, broker integration, or real-money work.

## Blocking Issues

- no longer-history robustness package
- current environment cannot install or import `akshare`
- no sample split
- no cost sensitivity
- no delayed-execution sensitivity
- no longer-history report package
- no paper observation for this strategy
- M3b evidence is not complete for M4/QMT/live-adjacent work
- full-suite green status is not currently available because of two residual
  test issues recorded in `07_verification.md`

## Default Safe Option

Keep `etf_regime_rotation_v1` in research-only status.

## Not Allowed

- no real-money trading
- no investment advice or trading permission
- no bypass of `quant.risk`
- no QMT, broker, or live gateway work
- no weakening of gates, tests, event persistence, reconciliation, or alerts
