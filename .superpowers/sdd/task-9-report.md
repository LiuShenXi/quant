# Task 9 Report: Generic Report And Benchmarks

## Status

DONE

## RED tests run and expected failures observed

- `pytest tests/test_backtest_artifact_report.py tests/test_backtest_benchmark_report.py -q`
  - Baseline before changes: `2 passed in 0.16s`.
- `pytest tests/test_research_report.py -q`
  - RED observed: `3 failed in 0.71s`.
  - Expected failure: `TypeError: write_result() got an unexpected keyword argument 'data_root'`, proving the generic reporting/data-root surface was not implemented yet.

## GREEN tests run and pass output summary

- `pytest tests/test_research_report.py -q`
  - `3 passed in 0.55s`.
- `pytest tests/test_backtest_artifact_report.py tests/test_backtest_benchmark_report.py -q`
  - `2 passed in 0.16s`.
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q`
  - `26 passed in 0.82s`.
- `pytest -q`
  - `272 passed in 13.18s`.

## Commits created

- `feat: add generic research reports`

## Files changed

- `src/quant/backtest/reporting.py`
- `src/quant/backtest/results.py`
- `tests/test_research_report.py`
- `.superpowers/sdd/task-9-report.md`

## Report schema keys

- `not_trading_permission`
- `strategy_id`
- `strategy_metrics`
- `turnover`
- `rebalance_count`
- `time_in_cash`
- `time_by_symbol`
- `total_fee`
- `estimated_slippage_cost`
- `cost_preset_name`
- `costs`
- `benchmarks`
- `data_period`
- `timezone`
- `risk_stop_summary`
- `dataset_manifest_copied`

## Concerns or compatibility notes

- `write_result` remains backward compatible and now accepts optional `data_root`. When supplied, configured non-cash benchmarks are generated from the dataset and `dataset_manifest.yaml` is copied if present.
- Existing callers that do not pass `data_root` still receive `report.json` and `report.md`; non-cash configured benchmarks are marked `UNAVAILABLE` rather than guessed from a hard-coded dataset.
- `report.md` uses research-only language and avoids any paper/live/real-money permission wording.
