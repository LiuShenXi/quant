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
