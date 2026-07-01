# v1.2 Research Engine Final Review Fix Report

Commit: `fix: close research engine integration gaps`

## Tests Run

- RED: `pytest tests/test_research_engine_generality.py::test_daily_continuous_24x7_primary_uses_bar_clock_without_a_share_open tests/test_multitimeframe_context.py::test_context_history_raises_for_manifest_frequency_omitted_from_clock tests/test_research_engine_generality.py::test_manifest_quote_currency_must_match_account_currency tests/test_research_engine_generality.py::test_quote_currency_risk_limit_must_match_account_currency -q` -> 4 failed for the expected review findings.
- GREEN: same four-test command -> 4 passed.
- `pytest tests/test_research_engine_generality.py tests/test_import_boundaries.py -q` -> 12 passed.
- `pytest tests/test_multitimeframe_context.py tests/test_config.py -q` -> 12 passed.
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q` -> 27 passed.
- `pytest -q` -> 281 passed.

## Files Changed

- `src/quant/backtest/engine.py`
- `tests/test_research_engine_generality.py`
- `tests/test_multitimeframe_context.py`
- `.superpowers/sdd/final-fix-report.md`

## Fix Summary

- Routed `primary_frequency="1d"` plus `calendar="continuous_24x7"` through the `BacktestClock` primary timeline instead of the legacy A-share daily session path.
- Made `ctx.history(..., freq=...)` fail fast when the frequency was not loaded into the backtest clock, preventing manifest-backed but undeclared frequencies from bypassing visibility state.
- Added account/dataset quote-currency validation and enforced `RiskMoneyLimit(unit="quote_currency", currency=...)` against the effective quote/account currency.

## Remaining Concerns

- No paper/live/QMT/broker paths were added or changed.
- Existing minor findings from the final review remain tracked in `.superpowers/sdd/progress.md`; this fix only closes the three Important findings.
