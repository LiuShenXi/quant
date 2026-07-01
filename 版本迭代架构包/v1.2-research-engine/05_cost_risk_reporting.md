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

## 3. 风险金额语义

所有金额类风控限制必须声明单位，不能裸写数字:

```yaml
risk:
  max_order_value:
    value: 10000
    unit: quote_currency
    currency: USD
  max_position_value:
    value: 60000
    unit: quote_currency
    currency: USD
  max_single_asset_exposure_pct: 0.60
```

允许单位:

- `quote_currency`: 账户报价币种金额，currency 必须等于 account currency。
- `currency`: 指定币种金额；若不同于 account currency，本轮不自动换汇，默认拒绝配置。
- `equity_pct`: 占账户总权益百分比。

业务侧的 CNY equivalent 只能进入 research assumption 或 report 注释；引擎运行时必须使用明确 quote currency 或 equity percentage。

## 4. Portfolio Stop

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

### Re-Entry Predicate Contract

第一轮 re-entry predicate 可以由策略层或配置层提供布尔状态，但必须通过可审计输入对象进入风险组件。风险组件不能 hard-code breadth 规则，也不能直接调用策略信号函数。

最小输入:

```text
predicate_id
as_of
decision_time
required_cooling_until
inputs:
  - name
    source_component
    freq
    visible_bar_dt
    construction
    value
```

要求:

- `as_of` 必须等于或早于当前 decision time。
- 所有输入都必须来自已闭合 bar 或已持久化状态。
- 多频输入必须记录 `freq` 和 `visible_bar_dt`。
- predicate 结果必须写 `risk_reentry_check` event，包含 predicate id、inputs metadata、result、reason。
- 如果输入缺失、timestamp 大于 decision time、或无法证明 fully closed，默认 result 为 false，并记录拒绝原因。

## 5. Event Journal Schema

v1.2 的 `events.jsonl` 是 append-only event journal，不是回测结束后从 orders/trades 派生的摘要文件。每行一个 JSON object，最小 schema:

```json
{
  "run_id": "research-run-id",
  "seq": 1,
  "event_type": "order_submitted",
  "timestamp": "2024-01-01T04:00:00Z",
  "source_component": "backtest.engine",
  "strategy_id": "example_strategy",
  "account_id": "backtest",
  "symbol": "AAA-USD",
  "order_id": "O-1",
  "trade_id": null,
  "risk_rule_id": null,
  "correlation_id": "target-batch-1",
  "payload": {}
}
```

要求:

- `seq` 在单个 run 内单调递增，不允许重排。
- journal append-only；修正用新 event 表达，不能改写旧 event。
- `event_type` 至少覆盖 target intent、rebalance decision、order submitted、order rejected、fill、cash transition、risk stop、cooldown start、re-entry check、engine state。
- 风控拒绝必须填 `risk_rule_id` 和 reason。
- order/trade CSV 可以由 journal 或内存对象导出，但不能替代 journal。

## 6. Reporting

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

## 7. Benchmarks

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
