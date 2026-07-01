# Experiment Design - Crypto Trend Breadth Top2

Status: `DESIGN_ONLY`
Strategy ID: `crypto_trend_breadth_top2_v1`

## Purpose

Define the first formal experiment matrix before data and engine gates are complete. This document is a research design, not a backtest result.

## Primary Baseline Strategy

Business defaults:

- Risk-on when at least 2 of BTC, ETH, SOL are in daily uptrend.
- Daily uptrend: daily close above 50-day EMA and 50-day EMA above its value 10 calendar days earlier.
- Rank assets by 20 closed 4-hour bar total return.
- Hold rank 1 at 60% and rank 2 at 40%.
- Rebalance at most once per UTC day.
- Move to stablecoin cash when risk-off.
- Stop to stablecoin cash after 20% active-cycle trailing drawdown.
- Wait 120 hours and require breadth recovery before re-entry.

## Cost Cases

- Mild: 10 bps fee plus 10 bps slippage per side.
- Baseline: 10 bps fee plus 20 bps slippage per side.
- Stress: 10 bps fee plus 50 bps slippage per side.

## Benchmarks

Required benchmark set:

- Stablecoin cash.
- BTC buy-and-hold.
- ETH buy-and-hold.
- SOL buy-and-hold.
- BTC/ETH/SOL equal-weight buy-and-hold.
- Top2 rotation without market breadth filter.
- Top2 rotation without portfolio drawdown stop.
- Top2 rotation with breadth but without cooldown.

## Minimum Metrics

- Total return.
- CAGR.
- Max drawdown.
- Calmar ratio.
- Annualized volatility.
- Turnover.
- Number of rebalances.
- Time in cash.
- Time in each asset.
- Fee paid.
- Slippage estimate.
- Best and worst regime contribution.
- Stop count and re-entry count.

## Sample Splits

Required:

- Full sample.
- First half / second half.
- Rolling 180-day and 365-day windows.
- Calendar-year returns.
- Bull, bear, and sideways regime buckets if the regime definition is specified before measuring results.

## Pass Conditions For Continuing Research

The strategy may continue from admission research to formal data/backtest review only if:

- Dataset audit can pass or pass with documented warnings.
- Formal baseline max drawdown does not exceed 35%.
- Baseline cost case does not lose to equal-weight buy-and-hold without meaningful drawdown improvement.
- Performance is not dominated by one SOL-only bull episode.
- Cost stress does not fully destroy the thesis.
- The 20% stop reduces severe left-tail loss after re-entry whipsaw is accounted for.

## Falsification Rules

Stop or redesign if:

- Any official baseline run with realistic costs exceeds 35% max drawdown.
- Results require same-bar execution or future daily data.
- Performance only appears under a manually selected date window.
- The no-stop or no-breadth ablation dominates with similar or lower drawdown, invalidating the added complexity.
- Turnover and costs dominate gross return.

## Notes For Technical Implementation

This matrix must be implemented through generic framework capabilities. The engine must not hard-code this strategy's assets, frequencies, indicators, weights, drawdown thresholds, or cooldown values.

