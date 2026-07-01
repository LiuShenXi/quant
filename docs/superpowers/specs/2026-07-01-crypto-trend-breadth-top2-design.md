# Crypto Trend Breadth Top2 Design

Date: 2026-07-01
Status: research-only design
Strategy ID: crypto_trend_breadth_top2_v1
CIO decision: RESEARCH_ONLY_DESIGN
Thesis status: THESIS_DRAFT
Risk decision: APPROVE_WITH_LIMITS for research design only

This document is not investment advice, investment recommendation, trading permission, paper approval, live approval, QMT approval, or broker integration approval.

## Purpose

Design a first research-only aggressive crypto spot strategy for wealth growth exploration while keeping explicit loss boundaries.

The original aspiration was to turn CNY 50,000 into CNY 200,000 within one year. That is a 300% return target and is treated only as an upside scenario target, not as a base expectation, promise, or approval to trade real money.

The strategy goal is:

- Preserve aggressive upside participation in high-liquidity crypto spot assets.
- Avoid leverage, futures, options, and broker/live integration in v1.
- Use explicit drawdown controls so the strategy is not a single all-in bet.
- Produce evidence that can later be reviewed by data, backtest, and risk agents.

## Strategy Summary

`crypto_trend_breadth_top2_v1` trades BTC, ETH, SOL, and a stablecoin cash state.

It uses daily bars to decide broad trend eligibility and 4-hour bars to rank the active assets. When the crypto market is broadly healthy, the strategy holds the strongest two assets. When the market is not broadly healthy, it exits to stablecoin cash.

Core rules:

- Asset universe: BTC spot, ETH spot, SOL spot, stablecoin cash.
- Frequency: 4-hour signal evaluation.
- Trade frequency cap: at most one rebalance per day.
- Market regime: risk-on only when at least two of BTC, ETH, and SOL are in daily uptrends.
- Risk-on allocation: top ranked asset 60%, second ranked asset 40%.
- Risk-off allocation: 100% stablecoin cash.
- Portfolio drawdown stop: if portfolio equity falls 20% from its recent peak, move to cash.
- Re-entry after stop: wait a 5-day cooling period and require market breadth to recover.
- Research hard red line: any tested variant with max drawdown worse than 35% cannot advance.

## Business Definitions For Implementers

These definitions are part of the business spec. They are meant to remove ambiguity for a later programming agent without turning this document into an engineering plan.

Market and time:

- Default research timezone: UTC.
- 4-hour bars are expected to close at 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 UTC unless the audited data source declares a different convention.
- Daily bars use UTC day boundaries unless the data audit chooses and documents another convention.
- A daily trend decision may only use the most recently fully closed daily bar.
- A 4-hour ranking decision may only use the most recently fully closed 4-hour bar.
- Signals generated from a closed bar may not fill on the same bar. The baseline research assumption is signal at closed bar, execution at the next modeled executable 4-hour bar price with configured fee and slippage.

Trend and breadth:

- Business default for a daily uptrend: daily close is above the 50-day EMA, and the 50-day EMA is above its value 10 calendar days earlier.
- Market breadth is risk-on only when at least two of BTC, ETH, and SOL satisfy the daily uptrend definition.
- If fewer than two assets are in daily uptrends, the target allocation is 100% stablecoin cash.
- The 50-day and 10-day values are v1 research defaults, not optimized parameters. Sensitivity may be reported, but the best sensitivity case cannot replace the baseline thesis.

Ranking and allocation:

- Rank only BTC, ETH, and SOL.
- Business default for 4-hour strength ranking: 20 closed 4-hour bar total return.
- Ties are broken by lower 20-bar realized volatility, then by BTC, ETH, SOL order.
- When risk-on and not stopped, allocate 60% to the top-ranked asset and 40% to the second-ranked asset.
- Rebalance at most once per UTC calendar day. If multiple 4-hour evaluations suggest changes on the same UTC date, only the first eligible rebalance may trade.
- If the target top two are unchanged, do not rebalance solely to correct small drift unless the implementation later defines a tested drift threshold.

Drawdown stop and re-entry:

- Portfolio trailing drawdown is measured from close-to-close total equity after modeled fees and slippage.
- The 20% trailing stop uses the active risk cycle peak. A new active risk cycle begins when the strategy enters risk-on after being fully in cash due to a stop.
- Full-sample max drawdown is still measured on the entire equity curve and must not exceed the 35% research hard red line.
- A stop event moves the target allocation to 100% stablecoin cash.
- The 5-day cooling period means 120 hours after the stop event timestamp under the research timezone.
- Re-entry requires both conditions: cooling period elapsed and market breadth risk-on using fully closed daily data.

Stablecoin cash:

- Stablecoin cash is a zero-yield quote-currency state for v1 research.
- Stablecoin issuer, depeg, custody, exchange, and yield risks are acknowledged but not modeled as alpha sources.
- The data audit must identify whether the quote currency is USDT, USDC, USD, or another proxy before backtest validation.

## Hypothesis

If BTC, ETH, and SOL exhibit persistent trend regimes and cross-sectional leadership, then a daily trend breadth filter plus 4-hour top-two rotation may capture upside better than passive crypto exposure while reducing severe drawdowns through cash exits and portfolio-level stop rules.

## Evidence

Current evidence is only a structured thesis. No crypto dataset, data audit, backtest artifact, benchmark comparison, paper observation, or live evidence exists yet.

Existing repository evidence from ETF research shows that execution assumptions, costs, timeline semantics, and benchmarks can materially change conclusions. This strategy must therefore be validated with realistic crypto costs and 7x24 execution semantics before any promotion discussion.

## Assumptions

Most important assumption: trend and breadth behavior in BTC, ETH, and SOL is strong enough to overcome 4-hour churn, fees, slippage, and false risk-on/risk-off transitions.

Other assumptions:

- BTC, ETH, and SOL have sufficient spot liquidity for the research capital size.
- Stablecoin cash is treated as a cash-like state for backtest accounting, but stablecoin issuer, depeg, custody, and exchange risks remain outside v1.
- Daily trend confirmation reduces noise enough to justify slower response.
- Daily max one rebalance lowers cost drag without missing the majority of trend moves.
- A 20% portfolio trailing drawdown stop reduces severe losses without making re-entry too slow.
- A 5-day cooling period is a research default, not an optimized parameter.

## Falsifiers

Reject or redesign the thesis if any of these occur:

- Max drawdown exceeds 35% in the baseline or realistic stress runs.
- Baseline performance under 10 bps fee plus 20 bps slippage is worse than simple BTC, ETH, SOL, or equal-weight holding without materially lower drawdown.
- Results depend almost entirely on one SOL-only bull regime.
- The 20% drawdown stop fails to reduce tail risk after accounting for re-entry whipsaw.
- Cost stress causes the strategy edge to disappear.
- The strategy requires high turnover or execution precision that cannot be modeled with available data.
- Data audit finds gaps, duplicated bars, stale data, exchange anomalies, or survivorship effects that change the conclusion.

## Validation Design

The first validation package must compare the strategy against simple, inspectable baselines:

- Stablecoin cash.
- BTC buy-and-hold.
- ETH buy-and-hold.
- SOL buy-and-hold.
- BTC/ETH/SOL equal-weight buy-and-hold.
- Top2 rotation without market breadth filter.
- Top2 rotation without portfolio drawdown stop.

Minimum metrics:

- Total return.
- CAGR.
- Max drawdown.
- Calmar ratio.
- Volatility.
- Turnover.
- Number of rebalances.
- Time in cash.
- Time in BTC, ETH, and SOL.
- Fee and slippage paid.
- Best and worst regime contribution.

Required sample checks:

- Full sample.
- First half and second half.
- Bull, bear, and sideways regimes if detectable from data.
- Mild cost case: 10 bps fee plus 10 bps slippage.
- Baseline cost case: 10 bps fee plus 20 bps slippage.
- Stress cost case: 10 bps fee plus 50 bps slippage.

Backtest artifacts must include:

- `config_snapshot.yaml`
- `orders.csv`
- `trades.csv`
- `equity.csv`
- `events.jsonl`
- `report.md`

No backtest result alone can approve paper or live trading.

## Risk Design

Research-only risk boundaries:

- No leverage.
- No futures.
- No options.
- No margin.
- No shorting.
- No direct exchange or broker gateway.
- No live credentials.
- No real-money order generation.
- Strategy code must not bypass `quant.risk`.
- Drawdown, exposure, and kill switch behavior must be independently reviewable outside strategy logic.

Research limits:

- Initial research capital assumption: CNY 50,000 equivalent.
- Max gross exposure: 100% spot notional.
- Max single asset exposure: 60% in normal top-two mode.
- Cash state: 100% stablecoin.
- Portfolio trailing stop: 20%.
- Hard max drawdown review limit: 35%.
- Trade cap: at most one rebalance per day.

Risk review must reject promotion if capital, max order value, max position value, loss limits, daily loss limits, and kill switch behavior are not explicit.

## Framework Requirement Tickets

These tickets are for a later programming agent. They are not part of this design implementation.

These are generic framework capability requests, not custom engine work for `crypto_trend_breadth_top2_v1`. This strategy is only the first acceptance scenario for the new capabilities.

Framework generality guardrails:

- Engine modules must not import this strategy, reference this strategy ID, or branch on this strategy's name.
- Engine modules must not hard-code BTC, ETH, SOL, stablecoin symbols, 4-hour bars, daily bars, 50-day EMA, 20-bar ranking, 60/40 weights, 20% stop, 5-day cooldown, or 35% review limit.
- Asset universe, bar frequency, calendar, cost model, benchmark set, drawdown threshold, cooldown, and ranking/trend parameters must be configuration or strategy-layer inputs.
- Risk controls must remain independently reviewable and reusable; strategy-specific thresholds may configure generic risk components, but the risk engine must not contain strategy-specific signal logic.
- Data, execution, risk, and reporting changes should support at least one non-crypto or toy fixture in tests where practical, so the framework does not become a one-strategy adapter.
- The implementation may include `crypto_trend_breadth_top2_v1` as an example strategy or acceptance fixture, but not as a dependency of the framework.

### CRYPTO-DATA-001: Crypto Spot OHLCV Dataset

Support configurable crypto spot OHLCV import for arbitrary spot symbols and source-declared bar frequencies. BTC, ETH, and SOL 4-hour data are the first research dataset, not hard-coded framework assumptions.

Acceptance criteria:

- Store symbol, timestamp, open, high, low, close, volume, and quote volume when available.
- Detect duplicate `(symbol, timestamp)` bars.
- Detect missing expected 4-hour bars under a 7x24 calendar.
- Preserve exchange/source metadata.
- Produce deterministic data audit summaries.
- Accept the research universe from dataset metadata or config rather than from engine constants.

### CRYPTO-CALENDAR-001: 7x24 Market Calendar

Add a reusable 7x24 calendar mode for assets that trade continuously.

Acceptance criteria:

- Do not reuse A-share trading sessions or holiday calendars.
- Support daily aggregation boundaries in a declared timezone, defaulting to UTC for research unless overridden.
- Make missing bars explicit rather than silently skipping sessions.
- Expose the calendar as a selectable framework calendar, not as a crypto-strategy special case.

### MULTI-TF-001: Daily Trend Plus 4-Hour Execution

Allow strategies to use multiple bar frequencies in the same backtest without future leakage. Daily trend plus 4-hour execution is the first acceptance scenario.

Acceptance criteria:

- Daily state must only use data available at the decision time.
- 4-hour decisions cannot see incomplete future daily bars.
- Report the exact timestamp used for daily trend confirmation.
- The framework API should support configurable primary and secondary frequencies rather than fixed daily/4-hour names.

### CRYPTO-EXEC-001: Spot Quantity and Stablecoin Accounting

Support fractional spot quantities and quote-currency accounting for spot assets.

Acceptance criteria:

- Allow fractional base quantities.
- Track stablecoin cash separately from risky asset positions.
- Calculate equity in a declared quote currency.
- Persist every rebalance, fill, rejection, cash transition, and state change as events.
- Do not assume a single stablecoin symbol; quote currency must come from config or dataset metadata.

### COST-001: Crypto Fee and Slippage Model

Support reusable bps-based fee and slippage assumptions for asset classes that choose this cost model. Crypto spot is the first use case.

Acceptance criteria:

- Configure fee bps and slippage bps independently.
- Run mild, baseline, and stress cost presets.
- Include total fee, estimated slippage cost, and turnover in the report.
- Cost presets must be named configurations, not hard-coded to this strategy.

### RISK-001: Portfolio Drawdown Stop and Re-Entry Gate

Support configurable portfolio-level trailing drawdown stops, cooling periods, and re-entry gates as reusable risk components.

Acceptance criteria:

- Track rolling portfolio peak.
- Trigger a configured defensive target when the configured drawdown threshold is breached; 20% cash exit is this strategy's first scenario.
- Enforce a configured cooling period; 5 days is this strategy's first scenario.
- Support a configured re-entry predicate; breadth recovery is this strategy's first scenario.
- Persist risk stop and re-entry events.
- Make this independently testable outside the strategy's signal logic.

### REPORT-001: Generic Strategy Benchmark Report

Generate configurable benchmark reports for research strategies. Crypto benchmarks are the first scenario.

Acceptance criteria:

- Compare strategy to configured cash, single-asset, equal-weight, and ablated variants; cash, BTC, ETH, SOL, and equal-weight are this strategy's first benchmark set.
- Report return, CAGR, max drawdown, turnover, time in cash, and costs.
- Emit machine-readable JSON and human-readable Markdown.
- Include a clear research-only disclaimer.

## Promotion Path

Required order:

1. Strategy thesis.
2. Data audit.
3. Backtest validation.
4. Risk review.
5. Paper observation plan.
6. Paper/live gatekeeper only if paper evidence later exists.
7. Human decision.

Current next step is not implementation of live trading. The next step is to create a research implementation plan for data ingestion, deterministic tests, backtest semantics, and reporting.

## Blocking Issues

- No crypto dataset has been audited.
- Current repository default assumptions are A-share/ETF oriented and may not support 7x24 crypto semantics.
- Multi-timeframe daily plus 4-hour behavior needs explicit anti-leakage rules.
- Stablecoin cash risk is not modeled.
- No strategy code, config, artifact, report, or benchmark exists yet.
- No paper observation plan exists.
- No M3b signoff exists.

## Default Safe Option

Keep `crypto_trend_breadth_top2_v1` research-only. Do not paper, live, connect exchanges, connect brokers, increase capital, or generate real orders until later gates produce explicit evidence and human authorization.
