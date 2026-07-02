# Thesis Update - Crypto Trend Breadth Top2 Smoke Admission

Status: `THESIS_UPDATE`

## Hypothesis

The parent thesis remains unchanged: if BTC, ETH, and SOL exhibit persistent
trend regimes and cross-sectional leadership, then a daily trend breadth filter
plus 4-hour top-two rotation may capture upside better than passive crypto
exposure while reducing severe drawdowns through cash exits and portfolio-level
stop rules.

## Evidence

- Parent thesis exists in
  `research/runs/2026-07-01T1703__crypto_trend_breadth_top2_admission/01_thesis.md`.
- Today's evidence is only strategy-contract and framework smoke evidence.
- No real crypto market dataset has been audited.
- No formal historical backtest result exists.
- Synthetic smoke output cannot prove edge, robustness, drawdown reduction, or
  tradability.

## Assumptions

Most important assumption: the strategy's market thesis still depends on real
BTC/ETH/SOL 4h and daily data quality. Today's synthetic data only exercises the
code path and artifact path.

Additional assumptions:

- Strategy code must stay in `strategies/` and rely only on the strategy
  contract plus allowed third-party libraries.
- Risk controls remain outside strategy logic.
- Signals use `ctx.now`, `ctx.history`, and closed bars exposed by the engine.

## Falsifiers

- Real data audit fails due to missing bars, unclear source semantics,
  duplicated timestamps, unstable quote-currency semantics, or unresolvable
  provider limitations.
- Formal baseline with realistic costs exceeds the 35% max drawdown red line.
- Baseline under 10 bps fee plus 20 bps slippage fails against equal-weight
  buy-and-hold without meaningful drawdown improvement.
- Synthetic smoke reveals same-bar execution, missing event journaling, or
  strategy imports outside the allowed contract boundary.

## Data Needed

- Audited BTCUSDT, ETHUSDT, SOLUSDT or equivalent spot 4h OHLCV.
- UTC candle open/close semantics.
- Source, exchange, quote currency, build command, and reproducibility metadata.
- Deterministic quality report with duplicate, missing-bar, OHLC, volume, and
  future-row checks.

## Validation Path

1. Synthetic smoke artifact.
2. Real data source probe and data audit.
3. Formal baseline backtest artifact only after data audit.
4. Backtest validation with costs, benchmarks, ablations, splits, and risk
   review.

## Next Decision

`VALIDATE_REAL_CRYPTO_DATA_SOURCE`

No paper/live/real-money decision is allowed from this thesis update.
