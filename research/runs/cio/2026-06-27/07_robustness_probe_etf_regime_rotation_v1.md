# Robustness Probe - ETF Regime Rotation v1

Status:

`NEEDS_MORE_EVIDENCE`

Question:

Does the existing ETF rotation backtest beat simple same-window ETF baselines on the inspected data window?

Data window:

```text
start=2025-06-03T15:00:00+08:00
end=2026-06-25T15:00:00+08:00
```

Results:

```text
ETF rotation v1:
  return_pct=20.10
  max_drawdown_pct=-6.49

510300.SH buy-and-hold close index:
  return_pct=27.57
  max_drawdown_pct=-9.94

510500.SH buy-and-hold close index:
  return_pct=59.30
  max_drawdown_pct=-14.02

Equal-weight close index:
  return_pct=46.30
  max_drawdown_pct=-11.36
```

Interpretation:

- The strategy does not beat simple long-only baselines on absolute return in this window.
- The strategy has lower max drawdown than the inspected close-index baselines.
- The thesis should be narrowed from "alpha versus simple ETF exposure" to "drawdown-controlled participation" unless longer-history evidence says otherwise.
- This probe is not enough to approve paper. It is a reason to hold and improve research evidence.

Required next checks:

- Longer-history benchmark comparison.
- Risk-adjusted metrics with consistent cost and exposure assumptions.
- Sample split by market regime.
- Cost sensitivity and delayed-execution sensitivity.
- Explicit decision on whether lower drawdown is worth the opportunity cost versus simpler baselines.

Next decision:

`HOLD_FOR_ROBUSTNESS`. Do not route to paper. Consider retiring this candidate if longer-history tests also fail to justify the lower-return/lower-drawdown tradeoff.

