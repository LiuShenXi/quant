# M3b to M4 Gate

## Required Evidence

- 10 counted trading days in paper observation.
- Daily reconciliation has zero difference for all counted days.
- One disconnect drill was performed and archived.
- CRIT alert delivery was verified.
- No unresolved manual intervention remains.
- Paper event stream and trade calendar are archived.
- Operator-authored `m3b_signoff.yaml` references the archived evidence.

## Required Command

Run this before any M4a or QMT work:

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

Only a successful validation output containing `M4a may start` can support the next engineering step.

## Blocking Conditions

- Missing signoff package.
- Fewer than 10 counted trading days.
- Any non-zero reconciliation difference.
- Missing disconnect drill.
- Missing verified CRIT alert delivery.
- Unresolved manual intervention.
- Any request to skip paper because a backtest looked good.

