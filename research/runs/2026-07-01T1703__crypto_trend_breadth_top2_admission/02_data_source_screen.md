# Data Source Screen - Crypto Trend Breadth Top2

Verdict: `FAIL`

Dataset reviewed: none
Intended use: future research-only crypto spot backtest
Strategy ID: `crypto_trend_breadth_top2_v1`

`FAIL` here means no dataset has been built or audited yet. It does not mean the strategy thesis failed.

## Candidate Sources

### Binance Spot Public Market Data

Initial status: `PREFERRED_FOR_FIRST_RESEARCH_DATASET`

Rationale:

- Binance Spot REST klines expose `GET /api/v3/klines`.
- Official docs list `4h` among supported intervals and include UTC-aware `startTime`, `endTime`, and optional `timeZone`.
- Binance also exposes public market-data-only URLs and historical files through Binance Data Collection.

Source notes:

- Official Spot market data docs: [Binance Spot market data endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
- Public historical data portal: [Binance Data Collection](https://data.binance.vision/)
- Public data repository notes: [binance-public-data](https://github.com/binance/binance-public-data)

Risks to audit:

- Pair availability and listing start dates for `BTCUSDT`, `ETHUSDT`, and `SOLUSDT`.
- Timestamp precision changes in public files.
- Whether Binance venue-specific history should be treated as exchange-specific rather than generic crypto market truth.
- Data access, rate limits, regional availability, and terms of use.

### Coinbase Exchange Candles

Initial status: `SECONDARY_CROSS_CHECK_SOURCE`

Rationale:

- Coinbase Exchange official candles endpoint is documented and can provide independent venue comparison.
- It supports 1 hour, 6 hours, and 1 day granularity, but not native 4-hour candles.

Source:

- [Coinbase get product candles](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)

Risks to audit:

- Native granularity does not match the strategy's 4-hour business definition.
- 4-hour candles would need aggregation from 1-hour data, which adds an extra data transformation and audit requirement.
- SOL history and quote pairs must be verified before use.

### CoinGecko OHLC / Market Chart

Initial status: `BENCHMARK_OR_SANITY_CHECK_ONLY`

Rationale:

- CoinGecko is useful for coin-level historical price sanity checks.
- Current docs show OHLC auto-granularity and range limits that do not cleanly provide long-history native 4-hour OHLC for this strategy.

Sources:

- [CoinGecko OHLC by ID](https://docs.coingecko.com/reference/coins-id-ohlc)
- [CoinGecko OHLC range](https://docs.coingecko.com/reference/coins-id-ohlc-range)
- [CoinGecko market chart range](https://docs.coingecko.com/reference/coins-id-market-chart-range)

Risks to audit:

- Coin-level data may aggregate across venues and not represent executable exchange candles.
- Long-history 4-hour OHLC availability is limited by plan and endpoint.
- Better as sanity check, not primary executable backtest source.

## Required Data Contract For First Dataset

Minimum fields:

- `symbol`
- `dt`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `source`
- `exchange`
- `bar_open_time`
- `bar_close_time`
- `data_status`

Required metadata:

- Provider and endpoint.
- Download/build command.
- Asset universe and quote currency.
- Date range.
- Timezone.
- Candle open/close semantics.
- Missing-bar policy.
- Whether volume is base or quote volume.

## Checks Required Before Backtest Validation

- Provider is named and reproducible.
- No duplicate `(symbol, dt)` rows.
- No missing expected 4-hour bars under 7x24 calendar, or every missing bar is documented.
- OHLC values are non-negative and internally plausible.
- Volume and quote volume are non-negative.
- Timestamp semantics are explicit and timezone-aware.
- Daily bars are derived only from fully closed 4-hour bars or independently audited daily bars.
- No future rows are available to a decision timestamp.
- Pair listing dates and symbol identity are documented.
- Stablecoin quote currency is explicit: USDT, USDC, USD, or other.

## Current Blocking Issues

- No local crypto dataset exists.
- No data build command exists.
- No quality log exists.
- No provider has been selected and accepted by data audit.
- Current repo data service is daily/A-share oriented and cannot yet formally audit 4-hour 7x24 crypto data under the same evidence standard.

## Required Fixes

1. Select a primary data source for the first research dataset.
2. Build a reproducible, read-only research dataset.
3. Run deterministic structural checks.
4. Produce a data audit artifact before any backtest credibility claims.

No backtest credibility conclusion should be inferred from unaudited data.

