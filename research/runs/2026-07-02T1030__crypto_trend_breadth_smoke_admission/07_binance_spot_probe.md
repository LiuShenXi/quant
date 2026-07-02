# Binance Spot Probe - Crypto Trend Breadth Top2

Verdict: `PROBE_PASS_WITH_WARNINGS_NOT_AUDITED_DATASET`

This is a data-source probe, not a formal data audit and not formal backtest
input.

## Source

- Provider: Binance Spot REST market data.
- Endpoint: `/api/v3/klines`.
- Official docs:
  `https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints`
- Probe window: 2026-06-01 00:00 UTC to 2026-06-08 00:00 UTC.
- Symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`.
- Intervals: `4h`, `1d`.

## Artifacts

- `artifacts/binance_spot_probe/quality_summary.json`
- `artifacts/binance_spot_probe/bars_4h_probe.csv`
- `artifacts/binance_spot_probe/bars_1d_probe.csv`
- `artifacts/binance_spot_probe/raw_BTCUSDT_4h.json`
- `artifacts/binance_spot_probe/raw_ETHUSDT_4h.json`
- `artifacts/binance_spot_probe/raw_SOLUSDT_4h.json`
- `artifacts/binance_spot_probe/raw_BTCUSDT_1d.json`
- `artifacts/binance_spot_probe/raw_ETHUSDT_1d.json`
- `artifacts/binance_spot_probe/raw_SOLUSDT_1d.json`

## Probe Checks

- HTTP access succeeded for all symbol/interval combinations.
- No duplicate open times were found in the probe.
- No OHLC plausibility failures were found in the probe.
- No negative volume or quote volume rows were found in the probe.
- Expected UTC 4h and 1d open slots were present.

## Warnings

- When `endTime` equals a kline open time, Binance returned the boundary row.
  The probe therefore has 43 rows for each 4h symbol and 8 rows for each 1d
  symbol, while a half-open 7-day window would expect 42 and 7.
- Formal downloader design must decide whether to subtract 1 ms from `endTime`,
  drop the boundary row, or use inclusive windows consistently.
- Binance data is exchange-specific. It is not generic crypto market truth.
- The strategy spec expects closed-bar decisions. Binance klines are identified
  by open time and include close time; the formal dataset contract must decide
  whether engine `dt` stores bar open time, exchange close time, or normalized
  interval close boundary.

## Required Next Action

Build a deterministic downloader and data quality report around this source
before requesting formal `data-audit-reviewer` review. Do not run formal
backtest validation from this probe.
