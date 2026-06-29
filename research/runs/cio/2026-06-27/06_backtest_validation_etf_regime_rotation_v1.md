# Backtest Validation - ETF Regime Rotation v1

Verdict:

`PASS_WITH_WARNINGS`

Backtest reviewed:

- Strategy: `etf_regime_rotation_510300_510500_v1`
- Original artifact directory: `量化使用记录2026-06-26/backtest/etf_regime_rotation_v1`
- Reproduction artifact directory: `research/cio-runs/2026-06-27/repro_etf_regime_rotation_v1`
- Strategy config: `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation_510300_510500.yaml`
- Dataset: `量化使用记录2026-06-26/data/etf_rotation_510300_510500_20250601_20260626`
- Intended decision: determine whether the existing backtest is credible enough to continue research. It is not paper approval.

Artifact inspection:

The repository does not contain `scripts/inspect_backtest_artifacts.py`, so the skill-requested inspection script could not be run. Equivalent deterministic checks were performed directly against the artifact files.

Required files:

```text
orders.csv: present
trades.csv: present
equity.csv: present
events.jsonl: present
report.md: present
config_snapshot.yaml: present
```

Original artifact metrics:

```text
orders=25
trades=25
equity_rows=518
event_lines=50
initial_value=100000.00
final_value=120098.30
return_pct=20.10
max_drawdown_pct=-6.49
rejected_orders=0
total_commission=553.70
```

Reproduction check:

Command:

```powershell
$env:PYTHONPATH = (Resolve-Path '量化使用记录2026-06-26\strategy_lab').Path
python scripts\run_backtest.py --strategy 量化使用记录2026-06-26\strategy_lab\etf_regime_rotation_510300_510500.yaml --data-root 量化使用记录2026-06-26\data\etf_rotation_510300_510500_20250601_20260626 --out research\cio-runs\2026-06-27\repro_etf_regime_rotation_v1 --initial-cash 100000
```

Result:

```text
repro orders=25
repro trades=25
repro equity_rows=518
repro event_lines=50
repro final_value=120098.30
repro return_pct=20.10
repro max_drawdown_pct=-6.49
repro rejected_orders=0
repro total_commission=553.70
equity_equal=True
orders_equal=True
trades_equal=True
```

Blocking issues:

None for continuing research from this artifact.

Warnings:

- The report file only records final value; it omits date range, initial capital, drawdown, costs, trade count, benchmark comparison, and assumptions.
- The backtest sample is short, roughly one year.
- Existing iteration notes say the strategy did not beat `510500` buy-and-hold over the inspected period.
- No sample split, out-of-sample test, cost sensitivity, window sensitivity, or parameter stability review is present.
- The selected two-ETF universe may be influenced by after-the-fact inspection unless a universe-selection rule is documented.
- Backtest logs are empty; reproducibility is supported by the rerun, config snapshot, and artifacts, not by original command logs.
- The dataset has a documented calendar/bar latest-date mismatch: bars end `2026-06-25`; calendar reaches `2026-06-26`.
- This review did not establish paper readiness.

Credibility notes:

- Artifact completeness is acceptable.
- Reproduction matched original orders, trades, and equity exactly.
- Costs are nonzero: commission total is `553.70`; backtest engine uses commission rate `0.00025` and minimum commission `5`.
- Backtest engine uses independent `RiskEngine` checks rather than strategy-internal risk only.
- Matcher includes volume cap, suspension, open limit-up, and open limit-down checks.
- Strategy signals at daily close and target orders are flushed on a later open path; this reduces same-day close-fill concern, but execution semantics still need explicit documentation in the final report.

Required next checks:

- Create a full report with date range, initial capital, final value, drawdown, costs, trade count, benchmark comparison, and assumptions.
- Run longer-history tests if data can be built reproducibly.
- Run sample split and cost sensitivity.
- Compare against `510300` buy-and-hold, `510500` buy-and-hold, equal-weight hold, and cash-filtered baselines.
- Document the ETF universe-selection rule before any paper discussion.
- Hold paper progression until the above checks and a subsequent risk review are complete.

Next decision:

`HOLD_FOR_ROBUSTNESS`. Continue research evidence building; do not route to paper. Risk review can be prepared after robustness checks produce a fuller backtest package.

