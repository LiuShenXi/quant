# 06 · 验收切片

## 1. 第一轮验收原则

验收必须证明框架泛化，而不是证明某个策略赚钱。

至少两类 fixture:

- `toy_multifreq_24x7`: 小型连续市场 fixture，用 AAA/BBB/CCC 这类非 crypto 名称，验证多频、7x24、fractional、bps 成本。
- `crypto_trend_breadth_acceptance`: 业务 acceptance fixture，可使用 BTC/ETH/SOL 配置，但只能依赖通用框架能力。

## 2. Slice A: Calendar And Dataset

验收:

- 7x24 calendar 能生成连续 4h expected timestamps。
- 缺失一个 expected 4h bar 时，data audit summary 稳定报错。
- A股日线旧 fixture 继续通过旧测试。
- dataset manifest 中的 timezone、quote currency、freq 被加载，不写死在引擎中。

## 3. Slice B: Multi-Timeframe No-Lookahead

验收:

- 4h 决策在日线未闭合前不能看到当天日线。
- `ctx.history(..., freq="1d")` 最后一行 `dt <= ctx.now`。
- report 或 events 中记录 daily confirmation timestamp。
- 构造一个会因未来日线泄露而错误交易的 fixture，测试必须证明不会交易。

## 4. Slice C: Execution And Accounting

验收:

- fractional quantity 可以成交和估值。
- account currency 来自配置，不固定 CNY。
- T+0 spot 可在下一 bar 卖出，A股 T+1 旧测试仍保持。
- target 在信号 bar 产生，最早下一 bar 成交。
- 每笔 rebalance、fill、rejection、cash transition 都进入 `events.jsonl`。

## 5. Slice D: Costs

验收:

- `fee_bps` 和 `slippage_bps` 可独立配置。
- mild/baseline/stress preset 输出不同 report，并保留 preset 名称。
- report 汇总 total fee、estimated slippage cost、turnover。
- A股成本模型旧测试仍通过。

## 6. Slice E: Portfolio Risk Overlay

验收:

- trailing peak 被独立追踪。
- drawdown breach 触发 defensive target 和 risk event。
- cooldown 未结束前不允许 re-entry。
- re-entry predicate 为 false 时继续 defensive target；为 true 时恢复允许开仓。
- 测试使用 toy predicate，不写死 breadth。

## 7. Slice F: Generic Report

验收:

- 输出 `report.json` 和 `report.md`。
- JSON 包含 `not_trading_permission: true`。
- benchmark 从配置生成 cash、single asset、equal-weight。
- report 不包含“可以 paper/live/真钱”的表述。

## 8. 不通过条件

任一情况出现，本轮失败:

- 引擎代码引用具体策略 ID。
- 引擎代码硬编码 BTC/ETH/SOL、4h、daily、EMA、60/40、20% stop、5-day cooldown。
- 策略可 import `quant.data`、`quant.backtest`、`quant.live`、`quant.risk` 或 `ops`。
- 风控只存在策略代码内部。
- 任何新增代码打开 exchange/broker/live gateway 路径。
