---
name: risk-governor
description: Use when reviewing quant strategy risk limits, position sizing, drawdown controls, order proposals, kill switches, or paper/live risk readiness.
---

# Risk Governor

Use this skill to evaluate whether a proposed strategy, config, or order flow respects risk boundaries.

## Workflow

1. Identify the account, strategy, mode, capital, instruments, and requested decision.
2. Inspect relevant risk config such as `config/risk/global.yaml`, strategy YAML, and paper/live config when present.
3. Load `references/live-risk-gates.md` for the gate checklist.
4. Check single-order, single-instrument, strategy-level, account-level, and daily drawdown exposure.
5. Check independent kill switch behavior and whether strategies can bypass risk.
6. End with `APPROVE_FOR_REVIEW`, `APPROVE_WITH_LIMITS`, or `REJECT`.

## Required Boundaries

- Do not approve live trading directly.
- Do not accept risk controls that live only inside strategy logic.
- Do not accept undefined capital, max position, max loss, or kill switch settings.
- Any unresolved reconciliation, alerting, or gateway issue is a rejection for live-money use.

## Output Shape

```markdown
Decision: APPROVE_FOR_REVIEW | APPROVE_WITH_LIMITS | REJECT

Scope:
Blocking risk issues:
Limit changes required:
Evidence reviewed:
Human signoff needed:
```

