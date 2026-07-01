# 02 · 目标架构

## 1. 架构增量

v1.2 不改变 modular monolith 和策略契约边界。新增或扩展的是平台内部的可复用组件:

```text
strategies/
  only quant.core.contract
        |
        v
quant.core.contract
  Bar / Context / StrategyBase / Account / Position / Order / Trade
        |
        v
quant.backtest
  clock / engine / matcher / results
        |
        +--> quant.data
        |      dataset metadata / calendar / bars / history
        |
        +--> quant.risk
        |      pre-trade checks / portfolio stops / state events
        |
        +--> quant.costs
               configured fee and slippage models
```

依赖方向仍是向内依赖契约，策略层不可见引擎内部。

## 2. 新组件职责

| 组件 | 所属模块 | 职责 |
| --- | --- | --- |
| `MarketCalendar` | `quant.data` 或 `quant.core` 候选 | 表达交易日历、连续市场、bar 边界和可交易时段 |
| `DatasetManifest` | `quant.data` | 描述 dataset 的频率、时区、quote currency、source、calendar 和 schema |
| `BarStore` / `DataService` 扩展 | `quant.data` | 按 `(symbol, freq)` 查询多频 bars，保证 `dt <= end` |
| `BacktestClock` | `quant.backtest` | 合并多 symbol、多 freq 的 bar 时间轴，保证确定性顺序 |
| `FrequencyState` | `quant.backtest` | 记录每个频率在当前决策时刻可见的最后闭合 bar |
| `SettlementRules` | `quant.core` 或 `quant.backtest` | 表达 T+0/T+1、qty step、lot size、fractional quantity |
| `QuotePortfolio` 扩展 | `quant.core` | 按配置 currency 估值，支持 fractional spot |
| `BpsCostModel` | `quant.costs` | fee bps 和 slippage bps 独立配置 |
| `PortfolioStop` | `quant.risk` | 组合级 trailing peak、stop target、cooldown、re-entry gate |
| `ResearchReport` | `quant.backtest` / scripts | 输出 JSON/Markdown benchmark 和成本、换手、cash time |

## 3. 配置入口

建议把 `StrategyConfig` 扩展为兼容旧配置的增量模型:

```yaml
id: example_research_slice
class: strategies.example:ExampleStrategy
version: "1.0.0"
universe: ["AAA", "BBB"]
frequencies:
  primary: "4h"
  history: ["1d", "4h"]
calendar: "continuous_24x7_utc"
account:
  currency: "USD"
  settlement: "t0"
costs:
  model: "bps"
  fee_bps: 10
  slippage_bps: 20
risk:
  max_gross_exposure_pct: 1.0
  max_position_value:
    value: 60000
    unit: "quote_currency"
    currency: "USD"
  max_single_asset_exposure_pct: 0.60
  portfolio_stop:
    enabled: true
    trailing_drawdown_pct: 0.20
    cooldown_hours: 120
params:
  ...
runtime_mode: backtest
```

旧配置 `freq: "1d"` 保留兼容，可在加载时映射为 `frequencies.primary = "1d"`。

## 4. 不变量

v1.2 必须新增这些不变量:

- `Bar.dt` 继续表示 bar 结束时间。
- `ctx.history(symbol, n, freq)` 只能返回 `dt <= ctx.now` 且已闭合的 bars。
- 多频回测中，低频状态必须显式记录它来自哪一根已闭合 bar。
- 任何 target/order 都不能在产生信号的同一根 bar 上成交。
- calendar/session 由配置选择，风控不得写死 A股时段。
- account currency、quote currency、settlement、qty step 来自配置或 instrument metadata。
- 金额类 risk limit 必须声明单位: `quote_currency` 金额、明确币种金额，或 `equity_pct` 百分比。
- `set_target_weight` 是 v1.2 第一轮策略契约的一部分，权重到数量的转换由框架处理。
- 所有状态变化事件必须符合 append-only event schema，不允许只在收尾阶段 dump 派生产物。
- research report 必须注明 `not_trading_permission: true`。
