# Task 10 Report

Status: DONE

## RED tests run and expected failures observed

- `pytest tests/test_research_engine_generality.py tests/test_import_boundaries.py -q`
  - Initial RED: `2 failed, 7 passed`; both failures were expected `FileNotFoundError` for missing fixture configs:
    - `tests/fixtures/toy_multifreq_24x7/strategy.yaml`
    - `tests/fixtures/crypto_trend_breadth_acceptance/strategy.yaml`
- After adding fixture files, the same command exposed small real platform compatibility gaps:
  - `RiskConfig` dropped `portfolio_stop` loaded from YAML.
  - Unit-declared `RiskMoneyLimit` values validated but were passed into numeric backtest risk checks.
  - `continuous_24x7` backtests still hit the legacy A-share session gate.

## GREEN tests run and pass output summary

- `pytest tests/test_research_engine_generality.py tests/test_import_boundaries.py -q`
  - `9 passed in 0.65s`
- `pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q`
  - `27 passed in 0.85s`
- `pytest -q`
  - `277 passed in 13.27s`

## Commits created

- `test: add research engine acceptance fixtures`

## Files changed

- `src/quant/backtest/engine.py`
- `src/quant/core/config.py`
- `src/quant/risk/pipeline.py`
- `tests/test_import_boundaries.py`
- `tests/test_research_engine_generality.py`
- `tests/fixtures/toy_multifreq_24x7/bars_1d.csv`
- `tests/fixtures/toy_multifreq_24x7/bars_4h.csv`
- `tests/fixtures/toy_multifreq_24x7/dataset_manifest.yaml`
- `tests/fixtures/toy_multifreq_24x7/instruments.csv`
- `tests/fixtures/toy_multifreq_24x7/strategy.yaml`
- `tests/fixtures/crypto_trend_breadth_acceptance/bars_1d.csv`
- `tests/fixtures/crypto_trend_breadth_acceptance/bars_4h.csv`
- `tests/fixtures/crypto_trend_breadth_acceptance/dataset_manifest.yaml`
- `tests/fixtures/crypto_trend_breadth_acceptance/instruments.csv`
- `tests/fixtures/crypto_trend_breadth_acceptance/strategy.yaml`

## Concerns or compatibility notes

- Platform code changes were limited to small bugs exposed by the acceptance tests:
  - YAML config now retains generic `risk.portfolio_stop`.
  - Backtest risk limits resolve validated money-limit units into numeric limits.
  - `RiskLimits.calendar == "continuous_24x7"` bypasses the legacy A-share session check while preserving the legacy default for configs without that calendar.
- The crypto acceptance fixture remains fixture/config-level only. Platform source scan covers `src/quant/backtest`, `src/quant/core`, `src/quant/data`, and `src/quant/risk` for `crypto_trend_breadth_top2_v1`, BTC/ETH/SOL hard-coding, `60/40`, 5-day cooldown, and 35% red-line literals.
- No paper/live/QMT/broker/real-money path was added.
