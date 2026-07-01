# Task 7 Report: Bps Fee And Slippage Cost Model

Status: DONE

## RED tests run and expected failures observed

- `pytest tests/test_bps_costs.py -q`
- First RED attempt failed during collection because `BpsCostModel` did not exist yet:
  - `ImportError: cannot import name 'BpsCostModel' from 'quant.costs'`
- Adjusted the test to import the existing module and fail inside test execution.
- Confirmed expected RED failure:
  - `4 failed, 1 passed`
  - Missing `quant.costs.BpsCostModel`
  - Missing `BacktestResult.cost_report_inputs`
  - Existing legacy A-share `CostModel(...).calculate()` assertion already passed.

## GREEN tests run and pass output summary

- `pytest tests/test_bps_costs.py -q`
  - `5 passed in 0.60s`
- `pytest tests/test_portfolio_costs.py tests/test_sim_gateway.py -q`
  - `9 passed in 0.42s`
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q`
  - `26 passed in 0.84s`
- `pytest tests/test_bps_costs.py -q`
  - `5 passed in 0.64s`
- `pytest -q`
  - `263 passed in 13.53s`

## Commits created

- `feat: add bps fee slippage cost model`

## Files changed

- `src/quant/costs.py`
- `src/quant/backtest/engine.py`
- `tests/test_bps_costs.py`
- `.superpowers/sdd/task-7-report.md`

## Cost accounting semantics

- Legacy `CostModel(commission_rate, commission_min, stamp_tax, transfer_fee).calculate()` behavior is preserved.
- New `BpsCostModel` applies `fee_bps` and `slippage_bps` independently.
- `Trade.commission` and portfolio cash use fee only.
- Slippage is exposed as `estimated_slippage_cost` in bps fill-event metadata and aggregate `BacktestResult.cost_report_inputs`.
- Slippage is not reflected in fill price; fill price remains the matcher result.
- Mild, baseline, and stress preset names are carried through `config.costs.preset` into report inputs. No preset values are hard-coded in strategies or the engine.

## Concerns or compatibility notes

- `ruff` was not available in the environment:
  - `ruff`: command not found
  - `python -m ruff`: `No module named ruff`
- No DataService, risk, portfolio/reporting, or live gateway files were changed.
