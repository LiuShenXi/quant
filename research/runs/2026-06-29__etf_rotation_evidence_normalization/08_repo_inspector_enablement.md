# Repo-Level Inspector Enablement

Status: `COMPLETE_FOR_ARTIFACT_COMPLETENESS`

## Change

Added a repository-level deterministic artifact inspector:

```text
scripts/inspect_backtest_artifacts.py
```

This closes the workflow gap where research runs had to reference the
backtest-validator skill's internal script path.

## Scope

The script checks:

- required file presence
- CSV parseability and row counts
- JSONL parseability, event counts, and invalid rows
- text file readability
- basic warnings for very short equity series or zero-order/zero-trade runs

It does not judge edge, paper readiness, live readiness, or investment merit.

## Evidence Generated

```text
artifacts/inspect_etf_regime_rotation_v1.json
artifacts/inspect_dual_ma_510300_20_60.json
```

Both inspected artifact directories returned:

```text
status=PASS
blocking_issues=[]
warnings=[]
```

## Remaining Gap

This is an artifact completeness inspector, not a full research report
generator. The next infrastructure step is still to generate metrics such as
return, drawdown, turnover, costs, rejected orders, benchmark comparisons, and
sample-split summaries from a single repo command.

