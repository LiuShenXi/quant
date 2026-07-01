# 敏感性预检 - ETF 轮动 v1

Verdict: `HOLD_FOR_EXECUTION_ROBUSTNESS`

## 目的

在修复风控、回测时间线、跨标的撮合、多标的日线 session 处理问题后，重新检查成本压力和单参数扰动是否立刻破坏 thesis，或暴露新的执行/风控问题。

本文件不是 paper/live 准入，也不是参数推荐。

## 方法

数据集：

`research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630`

基础配置：

```text
trend_window=60
momentum_window=20
target_exposure_pct=0.8
min_hold_days=5
score_buffer=0.01
max_order_value=100000
max_position_value=100000
max_gross_exposure_pct=0.95
```

修复后 artifact：

`artifacts/sensitivity_precheck_after_session_fix.json`

旧 `after_risk_fix` 和 `after_timeline_fix` artifact 已被取代，不再用于绩效解释。

## 结果摘要

| Case | Return | Max DD | Orders | Rejected | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 18.4487% | -29.4192% | 161 | 0 | session-fixed 基础结果 |
| cost_2x_rate | 14.6133% | -30.5412% | 161 | 0 | 成本压力后仍为正 |
| cost_4x_rate_2x_min | 7.5119% | -32.7009% | 161 | 0 | 高成本压力明显削弱收益 |
| trend_window_40 | 45.1010% | -17.8202% | 191 | 0 | 单参数扰动，不是推荐参数 |
| trend_window_80 | 36.9704% | -33.6202% | 154 | 0 | 回撤明显扩大 |
| momentum_window_10 | 38.4713% | -26.1287% | 212 | 0 | 换手升高 |
| momentum_window_40 | 24.7605% | -24.4291% | 135 | 0 | 无拒单 |
| score_buffer_0 | 31.3702% | -25.5321% | 215 | 0 | 换手最高 |
| score_buffer_0_02 | 14.1080% | -26.3574% | 131 | 0 | 弱于 baseline |
| min_hold_days_3 | 18.3077% | -28.2863% | 161 | 0 | 接近 baseline |
| min_hold_days_10 | 28.6247% | -28.0135% | 144 | 0 | 强于 baseline |

## 关键发现

所有预检 case 均无拒单，风控拒单污染暂未复现。

成本压力会明显压缩收益。`cost_4x_rate_2x_min` 下收益降至 `7.5119%`，最大回撤扩大至 `-32.7009%`。

参数扰动仍有正收益 case，但排序不稳定。`trend_window_40`、`momentum_window_10`、`trend_window_80` 表现较强，部分 case 换手更高或回撤更大；这些只能说明研究空间存在，不能作为参数推荐。

## CIO 解释

修复后，策略证据从“高收益低回撤”变成“收益优势不足且执行敏感”。它低于 `510300.SH`、`510500.SH` buy-and-hold 和等权持有，暂时不能作为完整策略。

当前最重要的问题不是继续找更优参数，而是先定义真实可执行口径，并检查该口径下是否仍有足够风险收益吸引力。

## 已修复的引擎问题

- `position_limit` 曾错误拒绝降低风险的 SELL 减仓单。
- 多标的日线处理曾允许同日收盘信号影响同日开盘执行。
- `_match_open_orders()` 曾允许订单被不同标的的 bar 撮合。
- 多标的日线 session 曾产生每标的一条 equity，并让收盘回调看到混合开盘/收盘估值。

验证结果：

```text
tests/test_backtest_engine.py tests/test_execution.py tests/test_paper_engine.py tests/test_oms.py tests/test_risk_pipeline.py: 49 passed
full test suite: 222 passed
ruff changed files: All checks passed
```

## 下一步

- 继续 research-only 执行鲁棒性审查。
- 增加现金、等权、单 ETF 持有、风险关闭方案的正式决策对照。
- 不继续生成 paper observation plan，直到完整敏感性审查和风险复核完成。
