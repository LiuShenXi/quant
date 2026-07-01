# Task 5 Report: Target Weight And Target-To-Order Conversion

Status: DONE

## RED Tests Run And Expected Failures Observed

- `pytest tests/test_target_weight_contract.py -q`
- Final RED result: `6 failed`
- Expected failure observed:
  - `AttributeError: 'BacktestContext' object has no attribute 'set_target_weight'`
  - `AttributeError: 'BacktestContext' object has no attribute 'set_target_value'`
- Note: an earlier RED attempt exposed a test helper setup error around `frequencies` passed through `model_copy`; that was corrected before implementation, then RED was rerun and failed for the intended missing API.

## GREEN Tests Run And Pass Output Summary

- `pytest tests/test_target_weight_contract.py -q`
  - `6 passed in 0.63s`
- `pytest tests/test_backtest_engine.py tests/test_import_boundaries.py -q`
  - `15 passed in 0.92s`
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q`
  - `26 passed in 0.84s`
- `pytest -q`
  - `253 passed in 13.28s`

## Commits Created

- `feat: add target weight contract`

## Files Changed

- `src/quant/core/contract/context.py`
- `src/quant/backtest/engine.py`
- `src/quant/core/sizing.py`
- `tests/test_target_weight_contract.py`
- `.superpowers/sdd/task-5-report.md`

## Target Event Payload Keys

`target_intent` events created by `set_target_value` and `set_target_weight` include:

- `source_bar_timestamp`
- `target_qty`
- `target_value`
- `target_weight`
- `valuation_price`

`target_intent_rejected` events reuse those keys when a sized target intent exists, and add `reason`.

## Concerns Or Compatibility Notes

- Risk Governor decision: APPROVE_FOR_REVIEW for research/backtest use only; this does not approve paper/live trading or real-money execution.
- Batch target weights are rejected when their gross target weight exceeds `risk.max_gross_exposure_pct`; no silent normalization was added.
- Quantity is sized from the signal-time visible mark price, then submitted no earlier than the next bar through the existing pending-target flush.
- Existing `ctx.set_target(symbol, target_qty)` event payload remains unchanged for legacy compatibility.
- Fractional sizing support is present in `quant.core.sizing`, but existing `DataService.get_instrument()` still casts `lot_size` and `qty_step` to `int`; this task did not touch `DataService` per scope.
