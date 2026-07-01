# 执行敏感性 - ETF 轮动 v1

Verdict: `HOLD_FOR_EXECUTION_ROBUSTNESS`

## 目的

在修复回测时间线、跨标的撮合、多标的日线 session 处理问题后，重新检查 `etf_regime_rotation_v1` 对成交假设的敏感程度。

本文件是 research-only 证据，不是 paper/live 准入，也不是参数推荐。

## 方法

数据集：

`research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630`

策略配置：

`research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/etf_regime_rotation_510300_510500.yaml`

执行压力：

- 滑点：成交价按方向恶化 `5 bps`、`10 bps`、`20 bps`。
- 额外执行延迟：在修复后的“信号后下一可成交开盘”基础上，每个 target 再多等待一个或两个 flush 周期。

修复后 artifact：

`artifacts/execution_sensitivity_after_session_fix.json`

扩展矩阵 artifact：

`artifacts/execution_pressure_matrix_after_session_fix.json`

旧 `after_risk_fix` 和 `after_timeline_fix` artifact 已被取代，不再用于绩效解释。

## 结果摘要

| Case | Return | Max DD | Orders | Rejected | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 18.4487% | -29.4192% | 161 | 0 | session-fixed 基准结果 |
| slippage_5bps | 11.0277% | -31.5545% | 161 | 0 | 轻度滑点 |
| slippage_10bps | 4.1660% | -33.7168% | 161 | 0 | 中等滑点 |
| slippage_20bps | -8.3175% | -37.7151% | 161 | 0 | 高滑点 |
| extra_one_flush_delay | 55.3888% | -13.9848% | 171 | 0 | 额外一周期执行延迟 |
| extra_one_flush_delay_slippage_10bps | 39.0274% | -17.3912% | 157 | 0 | 延迟 + 中等滑点 |

## 执行压力矩阵

| Delay | Slippage | Return | Max DD | Orders | Rejected |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 bps | 18.4487% | -29.4192% | 161 | 0 |
| 0 | 5 bps | 11.0277% | -31.5545% | 161 | 0 |
| 0 | 10 bps | 4.1660% | -33.7168% | 161 | 0 |
| 0 | 20 bps | -8.3175% | -37.7151% | 161 | 0 |
| 1 | 0 bps | 55.3888% | -13.9848% | 171 | 0 |
| 1 | 5 bps | 46.8231% | -15.3719% | 161 | 0 |
| 1 | 10 bps | 39.0274% | -17.3912% | 157 | 0 |
| 1 | 20 bps | 24.5306% | -21.3242% | 140 | 0 |
| 2 | 0 bps | 22.9445% | -26.0276% | 130 | 0 |
| 2 | 5 bps | 16.8610% | -28.1356% | 126 | 0 |
| 2 | 10 bps | 11.1867% | -30.2749% | 126 | 0 |
| 2 | 20 bps | 0.5161% | -34.5632% | 126 | 0 |

## 关键发现

所有执行压力 case 均无拒单，没有发现新的风控拒单污染。

修复后的 baseline 收益从旧口径 `88.5743%`、中间口径 `28.0922%` 下修至 `18.4487%`，最大回撤扩大至 `-29.4192%`。旧 baseline 不再可用。

滑点会显著削弱收益：`20 bps` 滑点下收益为 `-8.3175%`，并承受 `-37.7151%` 最大回撤。

额外延迟并非线性恶化，`delay_1` 在本窗口内反而高于 baseline。这不是利好结论，而是说明策略高度依赖执行时点和 regime 切换路径；单一 baseline 不能代表稳健收益。

## CIO 解释

策略 thesis 只能保留为继续研究假设：

```text
ETF 轮动可能降低某些路径下的回撤，但当前证据不足以证明稳定、可执行的 alpha。
```

修复后策略回报低于 `510300.SH`、`510500.SH` buy-and-hold 和等权持有，且在高滑点下可能亏损。它还不是风险控制型策略成品，只是待进一步定义执行口径的研究假设。

## 下一步

- 明确 paper 阶段可实现的实际执行口径。
- 把执行延迟从抽象 flush 周期映射到真实交易日开盘/收盘决策。
- 加入风险关闭、现金、等权持有、单 ETF 持有的正式决策对照。
- 不生成 paper observation plan，直到执行鲁棒性和风险复核完成。
