# Backtest Red Flags

## Artifact Red Flags

- Missing `config_snapshot.yaml`.
- Missing `events.jsonl`.
- Orders and trades cannot be reconciled.
- Report lacks date range, initial capital, ending value, drawdown, and cost assumptions.
- Equity curve has too few rows for the claimed conclusion.

## Market-Mechanics Red Flags

- No commission or slippage.
- Same-day close signal with same-day close fill unless explicitly modeled as impossible in live.
- Ignored lot size, liquidity, suspension, limit-up/limit-down, or T+1 constraints for markets where they matter.
- Fill prices look better than available market prices.

## Research Red Flags

- Best parameter chosen from a wide scan without out-of-sample confirmation.
- High return with very low trade count.
- Profit depends on one or two trades.
- Performance disappears when costs double.
- Strategy only works in one recent regime.
- Asset universe was selected after seeing performance.

## Promotion Rules

- A backtest can support paper testing.
- A backtest alone cannot support live trading.
- Paper/live promotion requires separate gate review.

