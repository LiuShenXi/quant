# Repo-Level Report Generator Enablement

Status: `COMPLETE_FOR_CORE_METRICS`

## Change

Added a repository-level deterministic report generator:

```text
scripts/report_backtest_artifacts.py
```

It builds on the artifact completeness check and adds core research metrics.

## Scope

The script reports:

- artifact completeness inspection
- period start and end
- equity row count
- initial and final value
- return percentage
- maximum drawdown percentage
- order count and rejected-order count
- trade count and traded symbols
- total commission
- SHA256 hashes for required artifact files
- explicit `not_trading_permission: true`

## Evidence Generated

```text
artifacts/report_etf_regime_rotation_v1.json
artifacts/report_dual_ma_510300_20_60.json
```

Current report highlights:

| Artifact | Return | Max drawdown | Trades | Commission |
| --- | ---: | ---: | ---: | ---: |
| `etf_regime_rotation_v1` | 20.0983% | -6.4892% | 25 | 553.70 |
| `dual_ma_510300_20_60` | -1.1024% | -7.1620% | 6 | 82.43 |

## Interpretation Boundary

These reports make artifact review easier. They do not prove strategy edge,
paper readiness, live readiness, or investment merit.

## Remaining Gap

The next report iteration should add benchmark comparisons and sample-split
summaries. Those are required before the ETF rotation thesis can move beyond
`HOLD_FOR_ROBUSTNESS`.

