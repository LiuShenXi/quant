# 01 · 迭代范围

## 1. 背景

CIO 提出的 `crypto_trend_breadth_top2_v1` 是第一组业务验收场景，但 v1.2 不是为了这个策略写一套特化引擎。它暴露的问题是 v1.1 平台默认假设偏 A股 ETF 日线:

- `StrategyConfig.freq` 只允许 `1d`。
- `DataService` 只读取 `bars_1d.csv`，并默认 `Asia/Shanghai`。
- 回测主循环按 A股日 session 分组，默认开盘撮合、收盘派发 `on_bar`。
- 风控交易时段检查写死 A股连续竞价。
- 账户币种固定 CNY，持仓默认 T+1，数量步长偏整手交易。
- 成本模型偏 A股佣金/印花税/过户费。

v1.2 要把这些变成可配置、可测试、可审计的框架能力。

## 2. 本轮目标

第一轮采用垂直切片，而不是一次性重写所有引擎:

```text
dataset metadata
-> calendar/session model
-> multi-frequency bar clock
-> no-lookahead context
-> target-to-order execution
-> quote-currency portfolio
-> bps cost/slippage
-> portfolio risk overlay
-> benchmark/report artifact
```

切片完成后，业务策略可以作为 acceptance fixture 或 example strategy 接入，但框架模块不得依赖它。

## 3. 明确非目标

本轮不做:

- 真实交易所或 broker gateway。
- ccxt、QMT、券商 SDK、真钱凭证、live overlay。
- Paper 观察、M3b 签核、M4/QMT 工程启动。
- Web 管理界面、分钟级生产行情、tick 高频、分布式回测。
- 为 `crypto_trend_breadth_top2_v1` 写死 BTC/ETH/SOL、4h、EMA50、20-bar return、60/40、20% stop、5-day cooldown 或 35% red line。

## 4. 版本结论

v1.2 的正确名字是 `research-engine`，不是 `crypto`。crypto top2 是第一个业务验收场景，平台目标是让以后 ETF、期货、crypto、toy fixture 都走同一套研究引擎语义。

## 5. 安全边界

当前结论:

```text
CIO Decision: BUILD_RESEARCH_ENGINE
Recommended next action: implement v1.2 vertical research slice after architecture review
Risk authorization needed: none for architecture and research-only backtest tooling
Blocking issues: no audited crypto dataset; no backtest artifact; no paper observation; no M3b signoff
Default safe option: keep all new capability research/backtest-only
Not allowed: paper/live/QMT/exchange/broker/real-money execution
```
