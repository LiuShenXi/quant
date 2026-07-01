# 决策日志

当研究方向、范围或阶段发生变化时，在这里追加一行。

| 日期 | 决策 | 范围 | 证据 | 默认安全动作 |
| --- | --- | --- | --- | --- |
| 2026-07-01 | `CONTINUE_RESEARCH_ONLY_ADMISSION` | `crypto_trend_breadth_top2_v1` 准入研究 | `runs/2026-07-01T1703__crypto_trend_breadth_top2_admission` 已形成 thesis、数据源筛选、实验设计、风险审查、framework gate；Binance Spot 是第一数据源候选但尚无本地审计数据；现有引擎仍缺 7x24/4h/multi-timeframe/quote-currency/generic drawdown gate | 继续 research-only；下一步只允许数据集构建与 data audit、通用 framework gate；不得 paper/live/交易所/真钱 |
| 2026-07-01 | `SET_POST_ETF_V1_RESEARCH_QUEUE` | ETF v1 退休后的研究队列 | `17_etf_rotation_v1_family_final_disposition.md` 已退休 v1 家族；候选路线图显示 DualMA 更适合作运维基线，`crypto_trend_breadth_top2_v1` 仅有 design spec，尚无数据审计/回测 | 下一主线只允许做 `crypto_trend_breadth_top2_v1` 准入审查；不得 paper/live/交易所/真钱；先过 thesis/data/framework gate |
| 2026-07-01 | `RETIRE_ETF_ROTATION_V1_FAMILY` | `etf_regime_rotation_v1`, `etf_regime_rotation_v1b_low_turnover` 最终处置 | 原始 v1 未通过执行、成本、固定暴露基准；v1b 依次未通过收益增强、滚动稳定性、简单固定暴露替代和多窗口路径平滑审查；最终处置见 `17_etf_rotation_v1_family_final_disposition.md` | 停止 v1/v1b 研究主线；不得 paper/live/QMT/真钱；不得继续扩大 v1/v1b 参数搜索；仅保留为研究素材和未来 ETF 仓位管理约束 |
| 2026-07-01 | `RETIRE_V1B_MAINLINE` | `etf_regime_rotation_v1b_low_turnover` 实验 B6 | v1b center 相对 fixed 40/50/60 equal-weight 的负收益窗口减少只在 504 日窗口为正：252 日为 -23，504 日为 +90，756 日为 -88；v1b best20 分别为 -24、+87、-36；路径平滑优势依赖窗口定义，不稳定 | 停止 v1b 主线；不得 paper/live/QMT/真钱；不得继续扩大 v1b 参数搜索；仅可作为未来 ETF 仓位管理研究的反例素材 |
| 2026-07-01 | `HOLD_FOR_PATH_SMOOTHING_UTILITY_REVIEW` | `etf_regime_rotation_v1b_low_turnover` 实验 B5 | fixed 40% equal-weight 收益 15.8263%、最大回撤 -20.0967%，同时优于 v1b center 的收益 12.9798%、最大回撤 -23.5427%；fixed 50% equal-weight 收益 19.7829%、最大回撤 -24.3739%，同时优于 v1b best20 的收益 16.7671%、最大回撤 -25.5298%；但 v1b center/best20 的 504 日负收益窗口为 568/571，少于 equal-weight 固定暴露的 658 | 继续 research-only；不得 paper/live/QMT/真钱；收益增强和最大回撤-收益效率 thesis 均不成立；下一步只允许证伪“负窗口减少/路径平滑”是否有独立投资意义 |
| 2026-07-01 | `CONTINUE_RESEARCH_ONLY_DRAWDOWN_CONTROL_THESIS` | `etf_regime_rotation_v1b_low_turnover` 实验 B4 | 相对 fixed 60% equal-weight，v1b center 少赚 10.7597 个百分点，换来 4.8614 个百分点最大回撤改善；504 日滚动窗口中负收益窗口少 90 个，回撤更低窗口 802/1068 个；best20 少赚 6.9724 个百分点，最大回撤改善 2.8743 个百分点 | 只保留“回撤控制/权益仓位管理”research-only thesis；不得 paper/live/QMT/真钱；下一步比较 fixed 40%/50%/60% 暴露曲线并定义适用/不适用场景 |
| 2026-07-01 | `HOLD_FOR_DRAWDOWN_CONTROL_THESIS_REVIEW` | `etf_regime_rotation_v1b_low_turnover` 实验 B3 | 2021-2023 失效区间与固定 60% ETF 基准弱 regime 重叠：v1b center 20 bps 为 -15.9617%，fixed 60% equal-weight 为 -18.8277%；但全周期 v1b center 12.9798%、best20 16.7671%，仍低于 fixed 60% equal-weight 23.7395% 和 fixed 60% 510500 34.8976%；滚动 504 日仍有 568/571 个负收益窗口 | 继续 research-only；不得 paper/live/QMT/真钱；不得再扩大参数搜索；下一步只允许审查“收益牺牲是否换来足够回撤控制” |
| 2026-07-01 | `HOLD_FOR_REGIME_STABILITY_REVIEW` | `etf_regime_rotation_v1b_low_turnover` 实验 B2 | 27 个邻域 case 中 15 个通过硬门槛，全部 20 bps 总收益为正且拒单为 0；但 0 个通过 504 交易日滚动稳定性，所有 case 在 20 bps 下 2021、2022、2023 均为负收益年度 | 继续 research-only；不得 paper/live/QMT/真钱；下一步只允许解释或证伪 2021-2023 regime 失效，不得扩大参数搜索追逐历史最优 |
| 2026-07-01 | `CONTINUE_RESEARCH_ONLY_LOW_TURNOVER_VARIANT` | `etf_regime_rotation_v1b_low_turnover` 实验 B | 3 个低换手 case 通过固定 gate；最佳 20 bps case `exposure_0_6_hold_40_buffer_0_05`：0 bps 收益 26.1822%、最大回撤 -19.0827%，20 bps 收益 12.9798%、最大回撤 -23.5427%，订单 93，换手 60.7123x | 只允许 research-only 下一轮稳定性验证；不得 paper/live/QMT/真钱；原始 v1 仍维持降级 |
| 2026-07-01 | `FAIL_RISK_OFF_BASELINE` | `etf_regime_rotation_v1` 实验 A | 策略平均暴露 45.4080%，43.4755% 交易日几乎空仓；baseline 收益 18.4487%、最大回撤 -29.4192%，弱于 equal-weight fixed 60% 的收益 23.7395%、最大回撤 -28.4041% | 继续维持 `DEMOTE_TO_RESEARCH_MATERIAL`；不得 paper；若实验 B 仍弱于固定暴露基准则停止该主线 |
| 2026-07-01 | `DEMOTE_TO_RESEARCH_MATERIAL` | `etf_regime_rotation_v1` CIO 处置 | session-fixed baseline 收益低于 510300/510500/等权持有；前半段收益 -2.1854%；20 bps 滑点收益 -8.3175%；不满足 paper execution gate | 原始 v1 不再作为候选策略推进；仅保留为 research-only 素材和可证伪实验来源 |
| 2026-07-01 | `NO_PAPER_EXECUTION_GATE` | `etf_regime_rotation_v1` 真实执行口径 | session-fixed baseline 收益 18.4487%，低于 510300/510500/等权持有；10 bps 滑点收益 4.1660%，20 bps 滑点收益 -8.3175%；延迟一周期表现更强，显示执行时点路径依赖 | 保持 research-only；不生成 paper observation plan |
| 2026-07-01 | `HOLD_FOR_EXECUTION_ROBUSTNESS` | `etf_regime_rotation_v1` session 修复后复测 | 修复多标的日线 session 阶段：开盘统一执行、收盘统一估值、每日一条 equity；全量测试 222 passed；修复后 baseline 收益 18.4487%、最大回撤 -29.4192%、拒单 0；20 bps 滑点收益 -8.3175% | 保持 research-only；旧 88.5743% 和 28.0922% baseline 均作废；继续定义真实执行口径 |
| 2026-07-01 | `PAUSED_ENGINE_BUG` | 回测引擎多标的日线估值/回调阶段 | 发现 equity 每标的记录一次，且首个标的收盘回调无法看到其他标的开盘成交和统一收盘估值；最大日内混合估值差异超过 5% | 暂停策略研究；先修复 session 处理并重跑研究证据 |
| 2026-07-01 | `HOLD_FOR_EXECUTION_ROBUSTNESS` | `etf_regime_rotation_v1` 时间线修复后复测 | 修复同日收盘到同日开盘时间倒置和跨标的撮合 bug；全量测试 221 passed；修复后 baseline 收益 28.0922%、最大回撤 -21.0963%、拒单 0；20 bps 滑点收益 0.7245%；后续 session 修复已取代该绩效口径 | 保持 research-only；旧 88.5743% baseline 作废；继续定义真实执行口径 |
| 2026-07-01 | `PAUSED_ENGINE_BUG` | 回测引擎时间线和撮合语义 | 回归测试显示 `AAA.SH` 收盘产生的 `BBB.SH` target 会在同日 09:31 创建；进一步发现 `BBB.SH` 订单可被 `AAA.SH` bar 以错误价格撮合 | 暂停策略研究；先修复回测引擎并重跑研究证据 |
| 2026-07-01 | `HOLD_FOR_EXECUTION_ROBUSTNESS` | `etf_regime_rotation_v1` 执行敏感性 | 滑点和额外一周期延迟压力均无拒单；10 bps 滑点下收益降至 65.9589%，额外一周期延迟降至 28.0922%，延迟加 10 bps 滑点降至 13.5633%；后续时间线/撮合修复已取代该绩效口径 | 保持 research-only；不生成 paper plan，继续执行鲁棒性研究 |
| 2026-07-01 | `HOLD_FOR_SENSITIVITY_REVIEW` | 风控引擎 `position_limit` 修复后 | 回归测试通过；全量测试 220 passed；`trend_window_40` 复测拒单从 24 降为 0 | 恢复 research-only 敏感性审查；仍不进入 paper |
| 2026-07-01 | `PAUSED_ENGINE_BUG` | 风控引擎 `position_limit` | 最小复现显示：当持仓已超过单标的上限时，`SELL` 减仓单如果减完后仍高于上限，会被 `position_limit` 拒绝；这会阻止风险降低订单 | 暂停继续策略研究；先修复并验证风控引擎，再恢复敏感性实验 |
| 2026-07-01 | `HOLD_FOR_RISK_CONFIG_REVIEW` | `etf_regime_rotation_v1` 敏感性预检 | 成本压力组无拒单；单参数扰动中 `trend_window_40` 出现 24 笔 `position_limit` 拒单，说明目标敞口和单标的持仓上限关系会污染参数绩效解释 | 暂停扩展敏感性研究；先审查风险配置一致性，不做 paper |
| 2026-07-01 | `HOLD_FOR_SENSITIVITY_REVIEW` | `etf_regime_rotation_v1` target 切片后长历史回测 | target 执行层按 `max_order_value` 切片；长历史回测订单拒单降为 0；收益 88.5743%，最大回撤 -13.1395%；后续时间线/撮合修复已取代该绩效口径 | 保持 research-only；进入成本/滑点、延迟执行、参数稳定性和现金基准审查 |
| 2026-07-01 | `HOLD_FOR_ORDER_SIZING_REVIEW` | `etf_regime_rotation_v1` 长历史鲁棒性 | `.venv` 数据依赖通过；2020-2026 AKShare 数据集已构建；长历史回测 artifact 检查通过；绩效报告显示 116 笔订单被 `max_order_value` 风控拒绝 | 保持 research-only；在审查订单 sizing/切片影响前，不用长历史绩效进入 paper 讨论 |
| 2026-07-01 | `CONTINUE_RESEARCH` | ETF 长历史数据构建 | `.venv` 中 `akshare 1.18.64` 和 `pandas 3.0.3` 可用；合并数据集覆盖 2020-01-02 至 2026-06-30 | 新数据集仅用于 research-only 审计和鲁棒性测试 |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | Longer-history ETF data build | `akshare` missing; pip install blocked by SSL/proxy errors; no partial dataset created | Keep research-only; do not make longer-history claims |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | ETF rotation current-window sample split | Sample-split report shows first-half underperformance and second-half concentration | Keep research-only; require longer-history robustness |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | ETF rotation current-window benchmarks | Repo-level benchmark report shows lower return and lower drawdown versus simple holds | Keep research-only; require sample-split and longer-history evidence |
| 2026-06-29 | `CONTINUE_RESEARCH` | Backtest core report infrastructure | Repo-level report generator added; ETF rotation and DualMA baseline reports generated | Use deterministic metrics reports before benchmark claims |
| 2026-06-29 | `CONTINUE_RESEARCH` | Backtest artifact inspection infrastructure | Repo-level inspector added; ETF rotation and DualMA baseline inspections returned `PASS` | Use deterministic artifact inspection before stronger backtest claims |
| 2026-06-29 | `HOLD_FOR_ROBUSTNESS` | `etf_regime_rotation_v1` | Current-path data/backtest checks, hashes, prior CIO package | Keep research-only and run robustness package |
| 2026-06-29 | Established canonical research workspace | All future quant research | User authorization plus repo constitution | Keep all work research-only unless gates pass |

## 决策层级

- `RESEARCH_ONLY`
- `CONTINUE_RESEARCH`
- `HOLD`
- `RETIRE`
- `PROMOTE_TO_REVIEW`
- `NEEDS_MORE_PAPER`
- `M4_BLOCKED`

AI 决策包只是证据整理，不是投资建议或交易批准。
