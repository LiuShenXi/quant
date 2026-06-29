---
name: data-audit-reviewer
description: Use when reviewing quant market data, bars, calendars, instruments, adjustment factors, data providers, or dataset readiness before research, backtest, paper, or live use.
---

# Data Audit Reviewer

Use this skill to decide whether a dataset is credible enough for the next workflow step.

## Workflow

1. Identify the dataset path, provider, asset universe, date range, and intended use.
2. Inspect repo-specific data contracts in `src/quant/data`, `data_sample`, and related config when available.
3. Load `references/data-quality-checklist.md` for the full checklist.
4. Check for missing bars, duplicate timestamps, non-trading days, stale calendars, invalid instruments, and adjustment-factor issues.
5. Look for future leakage: data available after `ctx.now`, same-day execution assumptions, or revised data used as if known historically.
6. End with `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`.

## Hard Fail Conditions

- Unknown data source for production/paper use.
- Missing trade calendar for daily-bar backtests.
- Adjustment factors absent or unexplained for adjusted-price strategies.
- Dataset contains future rows relative to the declared simulation time.
- Data quality issues are found but not documented in a quality log or review note.

## Output Shape

```markdown
Verdict: PASS | PASS_WITH_WARNINGS | FAIL

Dataset reviewed:
Intended use:
Blocking issues:
Warnings:
Checks performed:
Evidence:
Required fixes:
```

