Status: DONE

RED tests run and expected failures observed:
- `pytest tests/test_backtest_event_journal.py -q`
- Expected RED observed: collection failed with `ModuleNotFoundError: No module named 'quant.backtest.events'`.

GREEN tests run and pass output summary:
- `pytest tests/test_backtest_event_journal.py -q` -> `4 passed`
- `pytest tests/test_backtest_engine.py tests/test_backtest_artifact_report.py -q` -> initially failed only on the legacy `events.jsonl` golden byte comparison; after updating the golden to the new append-only schema -> `12 passed`
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q` -> `26 passed`
- `pytest -q` -> `246 passed`

Commits created:
- `feat: add append only backtest event journal`

Files changed:
- `src/quant/backtest/events.py`
- `src/quant/backtest/engine.py`
- `src/quant/backtest/results.py`
- `tests/test_backtest_event_journal.py`
- `tests/golden/events.jsonl`
- `.superpowers/sdd/task-4-report.md`

Event types implemented:
- `engine_state`
- `target_intent`
- `rebalance_decision`
- `risk_check`
- `order_submitted`
- `order_rejected`
- `fill`
- `cash_transition`

Concerns or compatibility notes:
- `events.jsonl` is now exported from recorded backtest journal events instead of end-of-run order/trade summaries; the existing order/trade/equity CSV exports are unchanged.
- `run_id` defaults to `StrategyConfig.id` for deterministic artifact generation; callers can pass `BacktestEngine(..., run_id=...)` when they need a distinct research run id.
- The first `engine_state` event is emitted before simulated market time advances, preserving lifecycle ordering with no strategy callback behavior change.
- No `quant.live.events` import was added.

## Task 4 Review Findings Requiring Fix

Reviewer: Ptolemy

Important:
1. `ctx.cancel()` / `BacktestEngine.cancel_order()` removes orders from `open_orders` without appending a journal event. This violates the global append-only audit constraint for order state changes. Add cancellation event coverage and tests.

Minor noted but not blocking:
- End-of-run pending target intents can remain unresolved in the journal. Track for later final review unless task fix naturally clarifies it.

## Task 4 Fix Report: Cancel Audit Event

Status: DONE

RED test run and expected failure observed:
- `pytest tests/test_backtest_event_journal.py::test_ctx_cancel_records_order_cancelled_event -q` -> failed with `assert 0 == 1` for missing `order_cancelled` journal events after `ctx.cancel()`.

GREEN tests run and pass output summary:
- `pytest tests/test_backtest_event_journal.py -q` -> `5 passed`
- `pytest tests/test_backtest_engine.py tests/test_backtest_artifact_report.py -q` -> `12 passed`
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q` -> `26 passed`

Commit:
- `fix: audit cancelled backtest orders`

Files changed:
- `src/quant/backtest/engine.py`
- `tests/test_backtest_event_journal.py`
- `.superpowers/sdd/task-4-report.md`

Fix summary:
- `BacktestEngine.cancel_order()` now marks the stored order as `CANCELLED`, removes it from `open_orders`, and appends an `order_cancelled` event with strategy/account/source/timestamp/order id/correlation id and payload reason.
- Added regression coverage through the public `ctx.cancel()` path so cancelled open orders cannot silently disappear from the append-only journal.

Remaining concerns:
- The reviewer minor about unresolved end-of-run pending target intents remains tracked for later review and was not changed by this focused cancel-audit fix.
