# CIO Decision Package - Crypto Trend Breadth Top2 Smoke Admission

CIO Decision: `SMOKE_ONLY_RESEARCH_CONTINUE`

## Strategy Opportunity

`crypto_trend_breadth_top2_v1` remains the active research-only crypto mainline.
The opportunity is unchanged from yesterday: test whether daily trend breadth
plus 4h top-two rotation can provide drawdown-controlled crypto upside
participation.

It remains a thesis, not an edge.

## Recommended Next Action

Complete synthetic artifact smoke, then move to real data source probe and data
audit. Do not run a formal strategy conclusion until real crypto data passes
audit.

## Candidate Strategies

Primary:

- `crypto_trend_breadth_top2_v1`

Future validation baselines:

- Stablecoin cash.
- BTC buy-and-hold.
- ETH buy-and-hold.
- SOL buy-and-hold.
- BTC/ETH/SOL equal-weight.
- Top2 without breadth.
- Top2 without portfolio stop.
- Top2 without cooldown.

## Evidence Reviewed

- Parent admission package.
- Current strategy implementation and tests.
- Synthetic smoke artifact:
  `artifacts/synthetic_smoke_result`.
- Artifact inspector output: `PASS_WITH_WARNINGS`.
- Binance Spot REST probe:
  `artifacts/binance_spot_probe/quality_summary.json`, verdict
  `PROBE_PASS_WITH_WARNINGS_NOT_AUDITED_DATASET`.
- Data audit explorer output: real crypto dataset remains `FAIL`.
- Strategy/engine explorer output: generic engine supports synthetic smoke, but
  strategy class had to be implemented.
- Backtest explorer output: formal crypto backtest artifact remains `FAIL`;
  synthetic smoke must be marked `SMOKE_ONLY`.

## Experiments To Run

Today:

1. Synthetic smoke artifact.
2. Artifact inspector on synthetic smoke.
3. Verification tests for strategy and runner.

Next:

1. Formal Binance downloader with inclusive/exclusive end-boundary handling.
2. Deterministic real-data quality report with hashes.
3. Cross-source sanity check.
4. Formal data audit.

## Sub-Agent Routing

- Data audit explorer: real dataset readiness.
- Strategy/engine explorer: strategy import and framework smoke readiness.
- Backtest explorer: artifact gate and smoke/formal boundary.
- CIO main thread: final synthesis and registry updates.

## Improvement Proposal

Promote the mainline from `NEEDS_DATA_AND_FRAMEWORK_GATE` to
`SMOKE_ONLY_RESEARCH_CONTINUE`. Do not add new crypto strategy variants until
the first real data audit is complete.

## Risk Authorization Needed

None for research-only synthetic smoke and data source probing.

Human authorization would be required before paper observation, exchange
connectivity, credentials, live-adjacent work, capital changes, or any
real-money discussion.

## Blocking Issues

- No audited real crypto dataset.
- Binance probe is successful but not an audited dataset.
- No formal crypto backtest artifact.
- No formal backtest validation.
- Synthetic full allocation plus fee accounting produced a small negative cash
  warning; formal research needs cost-aware sizing or cash buffer policy.
- No risk review for paper.
- No paper observation plan.
- No M3b signoff.

## Default Safe Option

Remain research-only.

## Not Allowed

- No investment advice.
- No investment recommendation.
- No trading permission.
- No paper/live/QMT/真钱 claim.
- No exchange or broker connection.
- No real orders or real credentials.
