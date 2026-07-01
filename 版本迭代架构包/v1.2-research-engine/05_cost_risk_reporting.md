# 05 · 成本、风控与报告

## 1. 成本模型

保留 A股成本模型，同时新增通用 bps 模型:

```yaml
costs:
  model: bps
  fee_bps: 10
  slippage_bps: 20
```

要求:

- fee 和 slippage 独立配置。
- slippage 作为估算成本进入 fill price 或成本字段，具体口径必须在 report 中声明。
- mild/baseline/stress preset 是命名配置，不写死在策略或引擎中。
- report 汇总 total fee、estimated slippage cost、turnover。

## 2. 风控时段泛化

`RiskEngine` 不应直接调用 A股连续竞价函数。交易时段检查应由配置提供:

```yaml
risk:
  trading_session:
    mode: calendar
    calendar: continuous_24x7
```

或由回测引擎传入一个已判定事实:

```text
is_tradable_now(symbol, now) -> bool
```

风险模块只负责拒绝不可交易时段订单并记录 `risk_rule_id=trading_session`。

## 3. Portfolio Stop

组合级 trailing drawdown stop 是独立风控组件，不属于策略信号。

最小状态:

```text
cycle_state: ACTIVE | STOPPED | COOLDOWN
cycle_peak_value
stop_triggered_at
cooldown_until
defensive_target
last_reentry_check
```

最小行为:

- 记录 active risk cycle 的 peak。
- 当 drawdown >= configured threshold，生成 defensive target。
- 触发后进入 cooldown，期间拒绝新开仓或覆盖目标到 defensive target。
- cooling period 结束后，调用配置的 re-entry predicate。
- stop、cooldown、re-entry 都写事件流水。

第一轮 re-entry predicate 可以是策略层/配置层提供的布尔状态输入；风险组件不能 hard-code breadth 规则。

## 4. Reporting

v1.2 result directory:

```text
results/{run_id}/
  config_snapshot.yaml
  dataset_manifest.yaml
  orders.csv
  trades.csv
  equity.csv
  events.jsonl
  report.json
  report.md
```

`report.json` 必须至少包含:

- `not_trading_permission: true`
- strategy metrics: total return, CAGR, max drawdown, Calmar, volatility
- turnover, rebalance count, time in cash, time by symbol
- total fee, estimated slippage cost
- benchmark metrics
- cost preset name
- data period and timezone
- risk stop events summary

`report.md` 是给人看的同内容摘要，必须包含 research-only disclaimer。

## 5. Benchmarks

Benchmark 不应写死 crypto。配置形态:

```yaml
benchmarks:
  - id: cash
    type: cash
  - id: buy_hold_AAA
    type: single_asset_buy_hold
    symbol: AAA
  - id: equal_weight_universe
    type: equal_weight_buy_hold
    symbols: ["AAA", "BBB", "CCC"]
  - id: ablation_no_stop
    type: strategy_variant
    params_patch:
      risk.portfolio_stop.enabled: false
```

第一轮可以先实现 cash、single asset、equal-weight；strategy variant ablation 可以进入下一小步，但接口要预留。
