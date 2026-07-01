# Strategy Thesis - Crypto Trend Breadth Top2

Status: `THESIS_DRAFT`
Strategy ID: `crypto_trend_breadth_top2_v1`
Run: `research/runs/2026-07-01T1703__crypto_trend_breadth_top2_admission`
Mode: research-only

## Strategy Identity

- Name: Crypto trend breadth top2 v1.
- Asset universe: BTC spot, ETH spot, SOL spot, stablecoin cash.
- Bar frequency: daily trend state plus 4-hour ranking/execution state.
- Holding horizon: multi-day to multi-week, with at most one rebalance per UTC day.
- Intended mode: research only.

## Hypothesis

If BTC, ETH, and SOL exhibit persistent trend regimes and cross-sectional leadership, then a daily trend breadth filter plus 4-hour top-two rotation may capture upside better than passive crypto exposure while reducing severe drawdowns through cash exits and portfolio-level stop rules.

## Evidence

- Observed market behavior: not yet independently measured in this repository.
- Prior research or source: business design spec only.
- Backtest evidence: none.
- Paper evidence: none.
- Contradictory evidence: prior ETF research showed that seemingly attractive rotation results can fail after execution semantics, costs, baselines, and regime stability are reviewed.

## Assumptions

Most important assumption: trend and breadth behavior in BTC, ETH, and SOL is strong enough to overcome 4-hour churn, fees, slippage, and false risk-on/risk-off transitions.

- Data assumption: a reproducible 4-hour OHLCV dataset exists for BTC/ETH/SOL spot pairs with stable UTC semantics, no hidden survivorship change, and auditable missing-bar handling.
- Execution assumption: signal at a fully closed bar can only execute on the next modeled executable 4-hour bar with configured fee and slippage.
- Regime assumption: crypto market leadership and breadth persist long enough for daily trend and 4-hour ranking to matter.
- Capacity/liquidity assumption: BTC/ETH/SOL spot liquidity is sufficient for the research capital assumption, but this must be validated by quote volume and turnover checks.
- Risk assumption: 20% trailing drawdown stop plus 120-hour cooldown reduces severe losses without destroying participation in strong regimes.

## Falsifiers

- Backtest falsifier: baseline cost case, 10 bps fee plus 20 bps slippage, underperforms BTC/ETH/SOL equal-weight without materially lower drawdown.
- Paper falsifier: any future paper observation shows repeated stop/re-entry whipsaw, reconciliation gaps, or unmodeled execution drift.
- Risk falsifier: max drawdown exceeds 35% in baseline or realistic stress runs.
- Data falsifier: audited data contains unexplained missing 4-hour bars, duplicated `(symbol, timestamp)` rows, unstable symbol mapping, or unclear quote-currency semantics.
- Time/regime falsifier: returns depend mainly on one SOL-only bull regime or one narrow market window.

## Data Needed

- BTC/USDT or BTC/USD spot OHLCV, 4-hour and daily-derived.
- ETH/USDT or ETH/USD spot OHLCV, 4-hour and daily-derived.
- SOL/USDT or SOL/USD spot OHLCV, 4-hour and daily-derived.
- Source metadata: exchange, pair, timezone, candle open/close semantics, volume units, quote volume, data availability window, download/build command.
- Quality report: duplicates, missing bars, OHLC plausibility, non-negative volume, expected 7x24 coverage, and source-specific limitations.

## Validation Path

1. Data source screening and dataset build plan.
2. Data audit.
3. Framework gate for 7x24, 4-hour, multi-timeframe, quote-currency accounting, and configurable risk components.
4. Minimal formal backtest with realistic costs.
5. Sensitivity and sample split checks.
6. Risk review.
7. Paper observation only after thesis/data/backtest/risk gates pass.

## Next Decision

`NEEDS_DATA_AND_FRAMEWORK_GATE`

The thesis is clear enough to continue research, but it is not evidence of edge and does not authorize paper, live, exchange connection, or real-money trading.

