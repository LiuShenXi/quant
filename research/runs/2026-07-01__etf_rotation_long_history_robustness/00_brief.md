# 研究简报 - ETF 轮动长历史鲁棒性

Run ID: `2026-07-01__etf_rotation_long_history_robustness`
创建日期: 2026-07-01
模式: research-only
策略 ID: `etf_regime_rotation_v1`

## 目标

恢复 2026-06-29 未完成的长历史数据构建，使用 2020-01-01 至 2026-06-30 的 `510300.SH` 与 `510500.SH` 日线数据，重新评估 ETF 轮动 v1 的长历史回测、benchmark、样本拆分和执行鲁棒性。

## 当前 CIO 结论

原始 v1 Decision: `DEMOTE_TO_RESEARCH_MATERIAL`

低换手 v1b Decision: `RETIRE_V1B_MAINLINE`

家族 Decision: `RETIRE_ETF_ROTATION_V1_FAMILY`

策略还没有建立成完整策略。修复回测时间线、跨标的撮合、多标的日线 session 处理问题后，旧 `88.5743%` 和 `28.0922%` baseline 均已作废；当前 session-fixed baseline 为：

```text
return_pct=18.4487
max_drawdown_pct=-29.4192
orders=161
trades=161
rejected_orders=0
equity_rows=1571
```

对比基准中，策略收益低于 `510500.SH` buy-and-hold 和等权持有，但最大回撤显著更低。因此当前 thesis 只能表述为：

```text
ETF 轮动可能提供回撤受控的 ETF 行情参与，但尚未证明稳定、可执行的 alpha。
```

默认安全动作：继续 research-only。不得进入 paper，不得调整 live/paper 风控边界，不得把本次长历史收益当成交易许可。

最新处置见 `09_cio_disposition_and_next_experiments.md`：原始 v1 不再作为候选策略推进，只保留为 research-only 素材和可证伪实验来源。

低换手变体 `etf_regime_rotation_v1b_low_turnover` 见 `12_v1b_low_turnover_stability.md`、`13_v1b_regime_failure_review.md`、`14_v1b_drawdown_control_thesis.md`、`15_v1b_fixed_exposure_substitution.md` 和 `16_v1b_path_smoothing_utility.md`：收益增强 thesis 不成立；最大回撤-收益效率 thesis 被 fixed 40%/50% 简单暴露削弱；路径平滑/负窗口减少优势只在 504 日窗口成立，在 252 和 756 日窗口不成立。因此 v1b 主线退休，只保留为研究素材；不得 paper/live/QMT/真钱。

最终家族处置见 `17_etf_rotation_v1_family_final_disposition.md`：ETF 轮动 v1 家族整体退休，不再从 v1/v1b 参数继续外推。

## 关键进展

- 当前 `.venv` 中 `pandas` 和 `akshare` 均可用，2026-06-29 的依赖阻塞已在本机恢复。
- 已生成长历史单标的和合并数据集：
  - `research/datasets/akshare_510300_20200101_20260630`
  - `research/datasets/akshare_510500_20200101_20260630`
  - `research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630`
- 已生成并重跑长历史回测 artifact：
  - `backtest/etf_regime_rotation_v1_long_history`
- Artifact 完整性检查为 `PASS`。
- 已修复 target 切片、风控 `position_limit`、日线时间线、跨标的撮合、多标的日线 session 处理问题。
- 修复后全量测试 `222 passed`。
- 已生成修复后研究 artifact：
  - `artifacts/sensitivity_precheck_after_session_fix.json`
  - `artifacts/execution_sensitivity_after_session_fix.json`
  - `artifacts/execution_pressure_matrix_after_session_fix.json`
- 已生成低换手 v1b 稳定性审查：
  - `artifacts/v1b_low_turnover_stability.json`
  - `12_v1b_low_turnover_stability.md`
- 已生成 v1b regime 失效归因：
  - `artifacts/v1b_regime_failure_review.json`
  - `13_v1b_regime_failure_review.md`
- 已生成 v1b 回撤控制 thesis 审查：
  - `artifacts/v1b_drawdown_control_thesis.json`
  - `14_v1b_drawdown_control_thesis.md`
- 已生成 v1b 简单固定暴露替代审查：
  - `artifacts/v1b_fixed_exposure_substitution.json`
  - `15_v1b_fixed_exposure_substitution.md`
- 已生成 v1b 路径平滑效用审查：
  - `artifacts/v1b_path_smoothing_utility.json`
  - `16_v1b_path_smoothing_utility.md`
- 已生成 ETF 轮动 v1 家族最终处置：
  - `17_etf_rotation_v1_family_final_disposition.md`

## 阻塞项

- 尚未定义真实 paper 可执行的成交语义：信号日、下单日、开盘/收盘、滑点和成交量上限。
- 执行敏感性很高，`20 bps` 滑点下收益降至 `-8.3175%`。
- 策略代码仍保存在历史 `strategy_lab`，不是正式 `strategies/` 包中的晋级策略。
- ETF 轮动 v1 家族已退休；不得继续扩大 v1/v1b 参数搜索。
- 没有 paper observation plan、M3b 签核包、paper/live gatekeeper 审查或人工风险授权。
