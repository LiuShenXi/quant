---
name: backtest-validator
description: Use when reviewing whether quant backtest results, strategy reports, orders, trades, equity curves, or config snapshots are credible before paper or live consideration.
---

# Backtest Validator

Use this skill to decide whether a backtest is credible enough to inform the next decision.

## Workflow

1. Identify strategy config, dataset, date range, cost model, artifact directory, and requested decision.
2. If an artifact directory exists, run `scripts/inspect_backtest_artifacts.py` with the artifact directory path and include the output summary.
3. Load `references/backtest-red-flags.md` for qualitative review.
4. Check realism: fees, slippage, lot size, T+1 behavior, limit-up/down or suspend handling where relevant.
5. Check robustness: parameter sensitivity, sample split, trade count, turnover, drawdown, and regime dependence.
6. End with `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`.

## Hard Fail Conditions

- Missing orders, trades, events, equity, report, or config snapshot for a production-style backtest.
- Backtest result cannot be reproduced from a declared config and dataset.
- Costs/slippage are zero or unspecified for paper/live promotion.
- Evidence of future leakage or strategy code branching on backtest/live mode.
- User asks to move to live without paper gate evidence.

## Output Shape

```markdown
Verdict: PASS | PASS_WITH_WARNINGS | FAIL

Backtest reviewed:
Artifact inspection:
Blocking issues:
Warnings:
Credibility notes:
Required next checks:
```
