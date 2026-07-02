# Research Brief - A-Share Limit-Up Continuation v0

Run ID: `2026-07-02T1114__a_share_limit_up_continuation_v0`
Created: 2026-07-02 11:14 +08:00
Timezone: Asia/Shanghai
Topic: A-share individual-stock short-horizon limit-up continuation research
Status: THESIS_DRAFT
Mode: research-only
Strategy ID: `a_share_limit_up_continuation_v0`

## Purpose

Turn the user's idea, "A股个股短线，吃涨停板快速滚雪球", into a falsifiable research candidate.

The research question is deliberately narrower:

Can A-share individual stocks that hit limit-up produce a reproducible, cost-aware, short-horizon continuation edge after realistic entry, exit, liquidity, and drawdown constraints?

This package is not investment advice, investment recommendation, paper approval, live approval, QMT approval, broker approval, or real-money trading permission.

## Scope

Asset universe: A-share individual stocks, initially Shanghai and Shenzhen listed common shares only; ST, delisting-risk, suspended, newly listed, and special-rule instruments are excluded until data proves they can be handled correctly.

Bar frequency: daily bars for event detection and next-session continuation study; intraday or order-book data is required before any claim about buying during a limit-up board.

Holding horizon: next session to 3 sessions after the limit-up event.

Execution assumption: research-only, conservative, next-session execution first. Same-day "board capture" must be treated as a separate, stricter experiment and cannot be validated from daily bars alone.

Out of scope:

- Strategy code.
- Backtest execution.
- Paper trading.
- QMT or broker integration.
- Real-money trading.
- Any claim that a limit-up event can actually be bought without intraday or order-book evidence.

## Thesis Snapshot

Hypothesis: If A-share individual stocks hit limit-up under favorable market breadth, sector strength, liquidity, and board-quality conditions, then next-session or 1-3 session continuation returns may improve versus unconditional limit-up events because attention, crowding, and order imbalance can persist briefly.

Most important assumption: the modeled entry and exit are realistically achievable after costs, failed-entry cases, failed-exit cases, and T+1 plus price-limit constraints.

Primary falsifier: the apparent edge disappears after conservative costs, failed execution, realistic exit constraints, or sample/regime splits.

## Data Requirements

Required datasets:

- A-share instruments and listing metadata.
- Exchange trading calendar.
- Daily OHLCV, amount, turnover, adjustment factors, and limit-up or limit-down fields.
- ST, suspension, delisting, IPO, and board classification flags.
- Market and sector breadth data.
- Intraday or order-book data before same-day board-capture research.

Required source evidence:

- Exchange rule references or vendor rule documentation for board-specific price limits and special cases.
- Reproducible data provider, retrieval date, version, and row counts.

Known data gaps:

- No audited dataset has been selected.
- No minute, tick, or order-book data has been approved.
- No survivorship-bias policy has been reviewed.
- No execution model has been validated.

## Experiment Plan

Baseline: event study on audited daily data. Detect limit-up events, then measure next-open, next-close, and 1-3 session forward returns with predefined exclusions.

Experiment matrix:

- `event_baseline`: unconditional limit-up events.
- `quality_filter`: seal strength proxy, turnover, volume, amount, prior trend, market breadth, and sector breadth.
- `cost_stress`: fees, taxes, slippage, failed entry, and failed exit.
- `regime_split`: bull, bear, sideways, high-volatility, mania, and unwind periods.
- `benchmark_ablation`: compare with simple momentum, high-volume, and market/sector baselines.

Metrics:

- Event count.
- Median, mean, and tail forward return.
- Win rate and payoff ratio.
- Maximum adverse excursion where available.
- Drawdown and worst event cluster.
- Cost-adjusted return distribution.
- Failed-entry and failed-exit sensitivity.

Pass conditions:

- Data audit is `PASS` or documented `PASS_WITH_WARNINGS`.
- Costs and execution assumptions are declared before results.
- Results are not dominated by a few events, a narrow date window, or post-hoc filters.
- Same-day board-capture claims are not made without intraday or order-book evidence.

Falsification rules:

- Reject or redesign if daily data is used to imply buyability at the limit-up price.
- Reject or redesign if realistic cost and failed execution assumptions destroy the effect.
- Reject or redesign if the effect exists only in one obvious bull or mania window.
- Reject or redesign if drawdown or tail loss would fail independent risk review.

## Decision Record

Latest decision: `RESEARCH_ONLY_THESIS_DRAFT`
Decision record file: `05_cio_decision_package.md`
Next decision owner: Codex research
Next review date: after data-source selection and data-audit triage

## Evidence Sources

- User prompt on 2026-07-02: desire to research A-share individual-stock short-term limit-up compounding.
- Repo constitution: `AGENTS.md`
- Promotion workflow: `docs/agents/workflow-strategy-promotion.md`
- Risk authorization hooks: `docs/agents/risk-authorization-hooks.md`
- Exchange rule references to be verified during data audit:
  - Shanghai Stock Exchange trading rules: https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20250519_10779396.shtml
  - Shenzhen Stock Exchange trading rules: https://www.szse.cn/lawrules/rule/stock/trade/t20230217_598773.html

## Blocking Issues

- Thesis is only a draft.
- No audited data.
- No backtest artifact.
- No execution model.
- No risk review.
- No paper observation.

## Default Safe Action

Keep research-only. Missing evidence must not be interpreted as approval to paper trade, trade live, connect QMT or a broker, or trade with real money.

## Not Allowed

- Paper approval.
- Live approval.
- Broker or QMT integration.
- Real-money trading.
- Real credentials, account identifiers, broker tokens, or live overlays.
