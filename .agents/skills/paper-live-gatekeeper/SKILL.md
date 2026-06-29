---
name: paper-live-gatekeeper
description: Use when deciding whether a paper-traded quant strategy, M3b observation package, or signoff artifact may advance toward M4, QMT, broker integration, or real-money live trading.
---

# Paper Live Gatekeeper

Use this skill as the strict gate between paper trading and any live-money work.

## Workflow

1. Identify the requested transition: paper continuation, M3b signoff, M4a start, QMT integration, or live-money approval.
2. Read the repo README and `docs/runbooks/m3b_signoff_template.yaml` if present.
3. Load `references/m3b-m4-gate.md`.
4. If an `m3b_signoff.yaml` path is provided, run `python scripts/validate_m3b_signoff.py <path>`.
5. Check 10 counted trading days, zero daily reconciliation differences, disconnect drill, verified CRIT alert delivery, and no unresolved manual intervention.
6. End with `M4_BLOCKED`, `M4A_MAY_START_FOR_HUMAN_REVIEW`, or `NEEDS_MORE_PAPER`.

## Non-Negotiable Boundary

This skill never approves real-money trading. It can only say whether the repo-defined preconditions appear satisfied for the next human-reviewed engineering step.

## Output Shape

```markdown
Decision: M4_BLOCKED | M4A_MAY_START_FOR_HUMAN_REVIEW | NEEDS_MORE_PAPER

Signoff artifact:
Validation command:
Blocking issues:
Evidence reviewed:
Next required action:
```

