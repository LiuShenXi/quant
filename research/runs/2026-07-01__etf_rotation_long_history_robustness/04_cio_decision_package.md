# CIO 决策包 - 2026-07-01

CIO Decision: `DEMOTE_TO_RESEARCH_MATERIAL`

## 策略机会

`etf_regime_rotation_v1` 仍是当前 ETF 轮动主线，但不再视为接近完成的策略。修复回测时间线、跨标的撮合、多标的日线 session 处理问题后，长历史收益显著下修。

当前 thesis 收窄为：

```text
ETF 轮动可能提供回撤受控的 ETF 行情参与，但尚未证明稳定、可执行的 alpha。
```

## 已审查证据

- 长历史 AKShare 数据集，覆盖 2020-01-02 至 2026-06-30。
- 修复后的长历史回测 artifact，完整性检查 `PASS`。
- 长历史 benchmark 和 sample split。
- target 切片、风控 `position_limit`、日线时间线、跨标的撮合、日线 session 处理修复后的测试证据。
- 修复后的敏感性预检和执行压力矩阵。

## 关键发现

- 长历史数据结构审查通过：3142 条 bars，1571 个交易日，无重复 `(symbol, dt)`，核心 OHLCV 空值为 0。
- 初次长历史回测有 116 笔 `max_order_value` 风控拒单；target 执行层切片后该拒单污染已解除。
- 风控引擎曾错误拒绝降低风险的 SELL 减仓单；已修复并补回归测试。
- 回测引擎曾存在时间线 bug：某标的收盘信号可能在另一标的同日开盘执行；已修复为按交易日先统一处理开盘 pending target，再处理收盘 `on_bar`。
- 回测撮合曾缺少 `order.symbol == bar.symbol` 过滤，跨标的订单可能被错误 bar 撮合；已修复并补回归测试。
- 多标的日线 session 曾每标的记录一次 equity，并让首个标的收盘回调无法看到其他标的开盘成交和统一收盘估值；已修复为全市场开盘执行、全市场收盘估值、每日一条 equity。
- 修复后全量测试：`222 passed`；相关测试：`49 passed`；ruff changed files: `All checks passed`。
- 修复后 baseline：收益 `18.4487%`，最大回撤 `-29.4192%`，订单/成交 `161/161`，拒单 `0`。
- 对比基准：`510300.SH` 收益 `20.9689%`、最大回撤 `-45.1007%`；`510500.SH` 收益 `58.1627%`、最大回撤 `-47.3145%`；等权收益 `39.5658%`、最大回撤 `-42.4382%`。
- 样本拆分：前半段收益 `-2.1854%`、最大回撤 `-23.9863%`；后半段收益 `20.5907%`、最大回撤 `-13.1262%`。
- 修复后敏感性预检 artifact：`artifacts/sensitivity_precheck_after_session_fix.json`，12 个 case 总拒单 `0`。
- 修复后执行敏感性 artifact：`artifacts/execution_sensitivity_after_session_fix.json`，6 个 case 总拒单 `0`。
- 修复后执行压力矩阵 artifact：`artifacts/execution_pressure_matrix_after_session_fix.json`，12 个 case 总拒单 `0`。
- `20 bps` 滑点下收益为 `-8.3175%`，最大回撤 `-37.7151%`。
- 额外一周期延迟在本窗口内反而提升至 `55.3888%`，说明策略高度依赖执行时点，不能用单一 baseline 代表稳健性。

## 决策

原始 `etf_regime_rotation_v1` 降级为 `DEMOTE_TO_RESEARCH_MATERIAL`。

不进入 paper，不进入 live，不接 QMT，不接真钱。当前策略还不是完整策略，只是一个仍值得研究的 ETF 风控参与假设。

后续只允许围绕 `09_cio_disposition_and_next_experiments.md` 中定义的可证伪实验继续 research-only，不再以原始 v1 形态争取 paper gate。

## 推荐下一步

1. 明确真实 paper 可实现的执行假设：信号日、下单日、开盘/收盘、滑点 bps、成交量上限。
2. 将“flush 延迟”映射到真实交易日执行语义。
3. 补充现金、等权、单 ETF 持有、风险关闭方案的统一对照。
4. 在固定真实执行口径后再做参数稳定性，不用单参数最优结果替代策略结论。
5. 若证据仍支持 thesis，再生成 paper observation plan 并重新进入 risk review。

## 风险授权需求

当前不需要人工授权，因为仅继续 research。

任何 paper/live-adjacent、M4/QMT、券商、真钱、资金规模、风险上限或交易行为变化都需要人工授权。

## 阻塞项

- 策略仍在历史 `strategy_lab`，不是正式策略模块。
- 尚未完成真实执行口径定义。
- 无 paper observation plan。
- 无 M3b 签核包和 paper/live gatekeeper 审查。

## 默认安全动作

保持 `etf_regime_rotation_v1` 为 research-only。不得 paper，不得 live，不得 QMT，不得真钱，不得绕过 `quant.risk`。
