# Data Quality Checklist

## Identity

- Provider is named.
- Download/build command is known.
- Asset universe is explicit.
- Date range is explicit.
- Timezone and market close semantics are explicit.

## Required Tables

- `bars_1d.csv` or equivalent OHLCV bars.
- `trade_calendar.csv` for market sessions.
- `instruments.csv` for symbol identity.
- `adjust_factors.csv` when adjusted prices are used.

## Structural Checks

- No duplicate `(symbol, dt)` rows.
- No missing OHLCV columns required by the strategy.
- OHLC values are non-negative and internally plausible.
- Volume is non-negative.
- Dates align with the trade calendar.
- Instrument codes are stable and map to the intended exchange.

## Leakage Checks

- No use of rows after the decision timestamp.
- No use of final close before the strategy is allowed to know it.
- No survivorship-only universe unless explicitly declared.
- No revised fundamentals or classifications treated as historically known.

## Paper/Live Readiness

- Latest data date matches the expected latest trading day.
- Build logs or quality logs are archived.
- Dataset path is versioned or reproducible.
- Any manual repair is documented.

