# Verification - 2026-06-29

## Commands Run

```powershell
python .agents\skills\backtest-validator\scripts\inspect_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\etf_regime_rotation_v1
python .agents\skills\backtest-validator\scripts\inspect_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\dual_ma_510300_20_60
python scripts\inspect_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\etf_regime_rotation_v1
python scripts\inspect_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\dual_ma_510300_20_60
python scripts\report_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\etf_regime_rotation_v1
python scripts\report_backtest_artifacts.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\dual_ma_510300_20_60
python scripts\report_backtest_benchmarks.py research\imported\usage_records\2026-06-26__quant_usage_record\data\etf_rotation_510300_510500_20250601_20260626 --symbols 510300.SH 510500.SH
python scripts\report_backtest_sample_splits.py research\imported\usage_records\2026-06-26__quant_usage_record\backtest\etf_regime_rotation_v1 research\imported\usage_records\2026-06-26__quant_usage_record\data\etf_rotation_510300_510500_20250601_20260626 --symbols 510300.SH 510500.SH
python scripts\check_data_dependencies.py --module pandas --module akshare
python scripts\build_akshare_etf_data.py --symbol 510300.SH --name 300ETF --start-date 20200101 --end-date 20260626 --out research\datasets\probe_510300_20200101_20260626
python -m pytest tests\test_quant_cio_skill.py tests\test_quant_agent_skills.py
python -m pytest
```

## Passing Evidence

`etf_regime_rotation_v1` artifact inspection:

```text
status=PASS
blocking_issues=[]
warnings=[]
orders_rows=25
trades_rows=25
equity_rows=518
event_rows=50
invalid_event_rows=0
```

`dual_ma_510300_20_60` artifact inspection:

```text
status=PASS
blocking_issues=[]
warnings=[]
orders_rows=6
trades_rows=6
equity_rows=259
event_rows=12
invalid_event_rows=0
```

Targeted quant agent tests:

```text
55 passed
```

Repo-level inspector test:

```text
tests/test_backtest_artifact_inspector.py
1 passed
```

Repo-level report test:

```text
tests/test_backtest_artifact_report.py
1 passed
```

Repo-level benchmark report test:

```text
tests/test_backtest_benchmark_report.py
1 passed
```

Repo-level sample-split report test:

```text
tests/test_backtest_sample_split_report.py
1 passed
```

Data dependency check test:

```text
tests/test_data_dependency_check.py
1 passed
```

Longer-history data dependency probe:

```text
pandas available: true
akshare available: false
status: FAIL
```

Longer-history build probe:

```text
RuntimeError: akshare is required for fetching real ETF data; install the data extra first
```

## Full Suite Residual Failures

Full suite result:

```text
213 passed
2 failed
```

Residual failures:

- `tests/test_import_boundaries.py::test_import_linter_contracts_are_kept`
  fails because `lint-imports` is not present beside the active Python
  executable on this Windows environment.
- `tests/test_paper_golden.py::test_paper_replay_matches_golden` fails because
  generated CSV uses LF line endings while `tests/golden_paper/orders.csv` uses
  CRLF. The visible CSV content matched in inspection; the byte comparison fails
  on line endings.

## Current Conclusion

Today's research package is created and the path migration issue caught by
`tests/test_quant_agent_skills.py` has been fixed. Full-suite green status is
not claimed because two unrelated residual failures remain.
