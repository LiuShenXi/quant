# Backtest Validation - Current Path Normalization

Verdict: `PASS_WITH_WARNINGS`

Backtest reviewed:

`research/imported/usage_records/2026-06-26__quant_usage_record/backtest/etf_regime_rotation_v1`

Requested decision:

Determine whether the current artifact can remain in the research evidence
package. This is not paper approval.

## Artifact Inspection

The backtest-validator skill provides
`.agents/skills/backtest-validator/scripts/inspect_backtest_artifacts.py`.
It was run against the current artifact directory and returned `PASS` with no
blocking issues or warnings. Additional direct artifact checks were also
performed against the current files.

Required files:

```text
orders.csv: present
trades.csv: present
equity.csv: present
events.jsonl: present
report.md: present
config_snapshot.yaml: present
```

Current metrics:

```text
orders_rows=25
trades_rows=25
equity_rows=518
event_lines=50
invalid_event_rows=0
initial_value=100000.00
final_value=120098.30
orders_sides={'BUY': 13, 'SELL': 12}
```

Config snapshot:

```text
strategy_id=etf_regime_rotation_510300_510500_v1
universe=['510300.SH', '510500.SH']
trend_window=60
momentum_window=20
target_exposure_pct=0.8
min_hold_days=5
score_buffer=0.01
max_order_value=100000
max_position_value=100000
max_gross_exposure_pct=0.95
runtime_mode=backtest
```

## Blocking Issues

None for preserving the artifact as research evidence.

## Warnings

- The report file only records final value and is not a complete backtest
  report.
- Sample period is short.
- The strategy underperformed same-window simple long-only baselines on
  absolute return in the 2026-06-27 robustness probe.
- No current longer-history, sample-split, cost-sensitivity, delay-sensitivity,
  or parameter-stability package exists.
- The repository now exposes `scripts/inspect_backtest_artifacts.py` for
  artifact completeness checks, but still lacks a full report generator.
- This artifact is not sufficient for paper admission.

## Hashes

```text
orders.csv
  SHA256=92A5505769C0CF2ACD8BCDDABC9B7A91EEF35C223E27032FBE08C3B306455C37
trades.csv
  SHA256=B5DCB64F630EAAA4432C3688FF2F9A2CAA0B76D9E7EB4E333BAA7794851DA7D9
equity.csv
  SHA256=BE9D9957D0E059FA77F0CBA7B15818715928F30113B20ADB348241DDAD5DE571
events.jsonl
  SHA256=5619947BC5C36381BCF21EA769034811C2FE582665532FFF6C1380FF4B04A21B
config_snapshot.yaml
  SHA256=96ACA58367F275B23AB3AFA795875903D1709770E446D31CF8532FE359B077F7
```

## Required Next Checks

- Create a complete backtest report generator or repo-level artifact inspection
  wrapper.
- Re-run the strategy on extended reproducible data.
- Compare against `510300.SH`, `510500.SH`, equal-weight, and cash/risk-off
  baselines.
- Run cost sensitivity and delayed-execution sensitivity.
- Run sample splits by market regime.
