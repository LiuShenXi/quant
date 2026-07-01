# 验证记录 - 2026-07-01

## 已运行命令

```bash
.venv/bin/python scripts/check_data_dependencies.py --module pandas --module akshare

.venv/bin/python scripts/build_akshare_etf_data.py --symbol 510300.SH --name 300ETF --start-date 20200101 --end-date 20260630 --out research/datasets/akshare_510300_20200101_20260630

.venv/bin/python scripts/build_akshare_etf_data.py --symbol 510500.SH --name 500ETF --start-date 20200101 --end-date 20260630 --out research/datasets/akshare_510500_20200101_20260630

.venv/bin/python scripts/merge_etf_datasets.py --input research/datasets/akshare_510300_20200101_20260630 --input research/datasets/akshare_510500_20200101_20260630 --out research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630

PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." .venv/bin/python scripts/run_backtest.py --strategy research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/etf_regime_rotation_510300_510500.yaml --data-root research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630 --out research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history --initial-cash 100000

.venv/bin/python scripts/inspect_backtest_artifacts.py research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history

.venv/bin/python scripts/report_backtest_artifacts.py research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history

.venv/bin/python scripts/report_backtest_benchmarks.py research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630 --symbols 510300.SH 510500.SH

.venv/bin/python scripts/report_backtest_sample_splits.py research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630 --symbols 510300.SH 510500.SH

.venv/bin/python -m pytest tests/test_backtest_engine.py::test_target_created_from_one_symbol_close_waits_until_next_day_open -q

.venv/bin/python -m pytest tests/test_backtest_engine.py::test_daily_multi_symbol_close_callbacks_see_session_open_fills_and_close_marks -q

.venv/bin/python -m pytest tests/test_backtest_engine.py tests/test_execution.py tests/test_paper_engine.py tests/test_oms.py tests/test_risk_pipeline.py -q

.venv/bin/python -m pytest -q

.venv/bin/python -m ruff check src/quant/backtest/engine.py tests/test_backtest_engine.py
```

另用修复后的引擎重建以下 research-only artifact：

```text
artifacts/sensitivity_precheck_after_session_fix.json
artifacts/execution_sensitivity_after_session_fix.json
artifacts/execution_pressure_matrix_after_session_fix.json
```

## 通过证据

```text
data dependency status: PASS
merged bars: 3142
merged instruments: 2
merged adjust_factors: 3142
merged calendar days: 1571
artifact inspection status: PASS
blocking_issues=[]
invalid_event_rows=0
orders_rejected=0
return_pct=18.4487
max_drawdown_pct=-29.4192
orders=161
trades=161
equity_rows=1571
targeted timeline/matching/session regression: 2 passed
targeted execution/risk tests: 49 passed
full test suite: 222 passed
ruff changed files: All checks passed
sensitivity after session fix: status=PASS, cases=12, rejected_total=0
execution sensitivity after session fix: status=PASS, cases=6, rejected_total=0
execution pressure matrix after session fix: status=PASS, cases=12, rejected_total=0
worst execution sensitivity case=slippage_20bps, return_pct=-8.3175
best execution sensitivity case=extra_one_flush_delay, return_pct=55.3888
```

## 已修复问题

```text
1. target 执行层按 max_order_value 切片，消除单笔金额拒单污染。
2. position_limit 允许降低风险的 SELL 减仓单通过。
3. 多标的日线回测按交易日处理，避免同日收盘信号被同日开盘执行。
4. open order 撮合按 order.symbol == bar.symbol 过滤，避免跨标的错误成交。
5. 多标的日线 session 改为开盘统一执行、收盘统一估值、每日一条 equity。
```

## 重要警告

```text
旧 after_risk_fix 和 after_timeline_fix 绩效 artifact 已被 session 修复后的 artifact 取代。
旧 baseline return_pct=88.5743 不再可用于策略判断。
中间 baseline return_pct=28.0922 也不再可用于策略判断。
当前 baseline return_pct=18.4487，低于 510300.SH、510500.SH buy-and-hold 和等权持有。
```

本轮不声明策略可进入 paper。策略保持 research-only；下一步必须定义真实可执行口径并继续执行鲁棒性审查。
