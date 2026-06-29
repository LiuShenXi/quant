# Decision Log

Append one row whenever a research decision changes direction, scope, or stage.

| Date | Decision | Scope | Evidence | Default safe action |
| --- | --- | --- | --- | --- |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | Longer-history ETF data build | `akshare` missing; pip install blocked by SSL/proxy errors; no partial dataset created | Keep research-only; do not make longer-history claims |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | ETF rotation current-window sample split | Sample-split report shows first-half underperformance and second-half concentration | Keep research-only; require longer-history robustness |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | ETF rotation current-window benchmarks | Repo-level benchmark report shows lower return and lower drawdown versus simple holds | Keep research-only; require sample-split and longer-history evidence |
| 2026-06-29 | `CONTINUE_RESEARCH` | Backtest core report infrastructure | Repo-level report generator added; ETF rotation and DualMA baseline reports generated | Use deterministic metrics reports before benchmark claims |
| 2026-06-29 | `CONTINUE_RESEARCH` | Backtest artifact inspection infrastructure | Repo-level inspector added; ETF rotation and DualMA baseline inspections returned `PASS` | Use deterministic artifact inspection before stronger backtest claims |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | `etf_regime_rotation_v1` | Current-path data/backtest checks, hashes, prior CIO package | Keep research-only and run robustness package |
| 2026-06-29 | Established canonical research workspace | All future quant research | User authorization plus repo constitution | Keep all work research-only unless gates pass |

## Decision Levels

- `RESEARCH_ONLY`
- `CONTINUE_RESEARCH`
- `HOLD`
- `RETIRE`
- `PROMOTE_TO_REVIEW`
- `NEEDS_MORE_PAPER`
- `M4_BLOCKED`

AI decisions are evidence packages, not investment advice or trading approval.
