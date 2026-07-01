# CIO Decision Package - Crypto Trend Breadth Top2 Admission

CIO Decision: `CONTINUE_RESEARCH_ONLY_ADMISSION`

## Strategy Opportunity

`crypto_trend_breadth_top2_v1` is a research-only aggressive crypto spot candidate. It targets upside participation in BTC/ETH/SOL regimes while using breadth, cash state, drawdown stop, and cooldown rules to avoid an all-in bet structure.

It remains a thesis, not an edge.

## Recommended Next Action

Proceed with data-source selection and dataset audit planning while technical implementation of generic framework capabilities happens separately.

The preferred first data source candidate is Binance Spot public market data, subject to data audit and terms review. Coinbase can be used as a secondary cross-check source where matching history and pair availability allow it. CoinGecko should be used only for sanity checks or benchmark context unless its endpoint limitations are resolved for long-history 4-hour OHLC.

## Candidate Strategies

Primary:

- `crypto_trend_breadth_top2_v1`

Ablations for validation:

- Top2 without breadth filter.
- Top2 without portfolio stop.
- Top2 without cooldown.
- BTC/ETH/SOL equal-weight.
- Single-asset buy-and-hold benchmarks.
- Stablecoin cash baseline.

## Evidence Reviewed

- Business spec: `docs/superpowers/specs/2026-07-01-crypto-trend-breadth-top2-design.md`
- Local framework review: `src/quant/backtest/engine.py`, `src/quant/data/service.py`, `src/quant/risk/pipeline.py`, `src/quant/backtest/results.py`
- Data quality checklist: `.agents/skills/data-audit-reviewer/references/data-quality-checklist.md`
- Binance Spot market data docs.
- Coinbase Exchange candles docs.
- CoinGecko OHLC and market chart docs.

## Experiments To Run

After data and framework gates:

1. Dataset audit for BTC/ETH/SOL spot 4-hour OHLCV.
2. Baseline strategy run under 10 bps fee plus 20 bps slippage.
3. Mild and stress cost sensitivity.
4. Benchmark comparison against cash, single assets, equal-weight, and ablations.
5. Split-sample and rolling-window stability review.
6. Regime contribution review.
7. Risk review.

## Sub-Agent Routing

Used sidecar agents for:

- Research package organization review.
- Local framework capability gap review.

The main CIO thread owns final decisions and repository evidence.

## Improvement Proposal

Keep `crypto_trend_breadth_top2_v1` as the main research line. Do not add more strategy candidates until this candidate either passes data/framework admission or fails a clear falsifier.

## Risk Authorization Needed

None for research-only documentation and data-source screening.

Future authorization required for:

- Paper observation.
- Exchange connectivity.
- Credentials.
- Live or broker-adjacent work.
- Capital/risk boundary changes.

## Blocking Issues

- No audited crypto dataset.
- No formal backtest artifact.
- Existing engine is daily/A-share oriented and cannot yet produce credible 7x24 4-hour crypto results.
- Stablecoin cash and quote-currency semantics are not modeled in formal artifacts.
- Report and event journal semantics are not yet rich enough for this strategy family; formal review needs metrics beyond final value and events beyond derived order/trade rows.
- No paper observation plan.
- No M3b signoff.

## Default Safe Option

Remain research-only. Do not paper, live, connect exchanges, connect brokers, use credentials, increase capital, or generate real orders.

## Not Allowed

- No investment advice.
- No investment recommendation.
- No trading permission.
- No live/QMT/真钱 claims.
- No backtest-profit-to-live inference.
- No strategy-specific framework customization.
