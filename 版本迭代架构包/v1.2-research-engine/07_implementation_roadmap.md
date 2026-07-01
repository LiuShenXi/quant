# 07 · 实施路线图

## 1. 推荐顺序

```text
Task 1: config and manifest models
Task 2: calendar and multi-frequency DataService
Task 3: BacktestClock and no-lookahead context
Task 4: quote-currency portfolio and settlement rules
Task 5: bps cost/slippage model
Task 6: portfolio risk overlay
Task 7: generic report and benchmarks
Task 8: crypto acceptance fixture and architecture compliance tests
```

每个 task 都必须 TDD: 先写失败测试，确认失败原因，再写最小实现。

## 2. 代码边界建议

候选新增文件:

```text
src/quant/data/calendar.py
src/quant/data/manifest.py
src/quant/data/bars.py
src/quant/backtest/clock.py
src/quant/core/settlement.py
src/quant/risk/portfolio_stop.py
src/quant/backtest/reporting.py
```

候选修改文件:

```text
src/quant/core/config.py
src/quant/core/contract/context.py
src/quant/core/contract/types.py
src/quant/core/portfolio.py
src/quant/costs.py
src/quant/data/service.py
src/quant/backtest/engine.py
src/quant/backtest/results.py
src/quant/risk/pipeline.py
tests/test_import_boundaries.py
```

保持 `core` 不依赖 `data/backtest/live/risk`。如果 `MarketCalendar` 需要被 risk 和 backtest 共用，优先放在 `quant.core` 或定义 `Protocol`，避免反向依赖。

## 3. 测试策略

新增测试应覆盖:

- `tests/test_calendar.py`
- `tests/test_dataset_manifest.py`
- `tests/test_multifrequency_data_service.py`
- `tests/test_backtest_clock.py`
- `tests/test_spot_portfolio_accounting.py`
- `tests/test_bps_costs.py`
- `tests/test_portfolio_stop.py`
- `tests/test_research_report.py`
- `tests/test_research_engine_generality.py`

旧测试必须继续跑:

```bash
pytest tests/test_backtest_engine.py tests/test_data_service.py tests/test_risk_pipeline.py tests/test_portfolio_costs.py tests/test_import_boundaries.py -q
```

最终整包验证:

```bash
pytest -q
```

## 4. 实施门禁

进入代码实现前需要:

- 本架构包已完成 review。
- implementation plan 写入 `docs/superpowers/plans/` 或用户指定位置。
- 当前未提交变更归属清楚，不能混入无关用户改动。

完成代码后仍然只是 research/backtest tooling。任何 paper/live/QMT/交易所/真钱相关请求，继续按 `paper-live-gatekeeper` 和 M3b 签核阻塞。

## 5. 后续扩展

v1.2 第一轮之后可继续扩展:

- strategy variant ablation runner。
- regime split and contribution report。
- provider adapter for audited crypto data。
- richer quote currency and stablecoin risk model。
- research run integration under `research/runs/`。

这些扩展都不能替代 thesis、data audit、backtest validation 和 risk review。
