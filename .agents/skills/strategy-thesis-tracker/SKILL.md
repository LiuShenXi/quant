---
name: strategy-thesis-tracker
description: Use when proposing, revising, or evaluating a quant strategy idea, alpha hypothesis, ETF rotation rule, signal thesis, or strategy kill condition.
---

# Strategy Thesis Tracker

Use this skill to keep strategy ideas explicit, falsifiable, and separate from production approval.

## Workflow

1. Identify whether the user needs a new thesis, an update, or a review of an existing thesis.
2. Load `references/thesis-template.md` when a structured thesis is needed.
3. State the strategy hypothesis in plain language before discussing indicators or code.
4. Separate evidence from assumptions. Mark anything untested as an assumption.
5. Define falsifiers: market behavior, backtest evidence, paper evidence, or risk behavior that would invalidate the thesis.
6. End with one of: `THESIS_DRAFT`, `THESIS_UPDATE`, `NEEDS_EVIDENCE`, or `REJECT_THESIS`.

## Required Boundaries

- Do not say a strategy should trade live.
- Do not treat backtest profit as proof of edge.
- Do not optimize parameters inside this skill; hand off to `backtest-validator`.
- Do not hide uncertainty. List the most important assumption first.

## Output Shape

```markdown
Status: THESIS_DRAFT | THESIS_UPDATE | NEEDS_EVIDENCE | REJECT_THESIS

Hypothesis:
Evidence:
Assumptions:
Falsifiers:
Data needed:
Validation path:
Next decision:
```

