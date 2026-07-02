# Data Audit Triage - Crypto Trend Breadth Top2

Verdict: `FAIL_FORMAL_DATASET`

Probe verdict: `PROBE_PASS_WITH_WARNINGS_NOT_AUDITED_DATASET`

Dataset reviewed: no real crypto dataset
Intended use: future research-only formal crypto spot backtest

## Evidence Reviewed

- Parent data screen:
  `research/runs/2026-07-01T1703__crypto_trend_breadth_top2_admission/02_data_source_screen.md`
- Parent CIO package:
  `research/runs/2026-07-01T1703__crypto_trend_breadth_top2_admission/06_cio_decision_package.md`
- Current synthetic acceptance fixture:
  `tests/fixtures/crypto_trend_breadth_acceptance/`
- Current data service and manifest code:
  `src/quant/data/service.py`, `src/quant/data/manifest.py`,
  `src/quant/data/quality.py`
- Binance Spot REST probe:
  `artifacts/binance_spot_probe/quality_summary.json`
- Parallel data-audit explorer conclusion: current real dataset status is
  `FAIL`.

## Blocking Issues

- No real provider dataset exists in the repository.
- No reproducible download/build command exists for BTC/ETH/SOL 4h data.
- No quality log exists for duplicates, missing 4h slots, OHLC plausibility,
  volume, quote volume, future rows, or UTC candle semantics.
- Binance Spot remains a preferred candidate source, not an accepted audited
  dataset.
- Coinbase and CoinGecko remain secondary/sanity candidates, not primary
  accepted research data.
- Binance probe found `endTime` boundary inclusion behavior: when `endTime`
  equals a kline open time, the API returned that boundary row. A formal
  downloader must define and test inclusive/exclusive window behavior.

## Warnings

- Existing crypto fixture is synthetic and cannot support market conclusions.
- Current data quality module is structural-minimal and does not yet represent
  a full crypto data audit report.
- Binance data is venue-specific and must not be treated as generic crypto
  market truth without documenting that limitation.
- Venue-specific Binance history should not be treated as generic crypto market
  truth without noting exchange-specific limitations.

## Checks Performed

- Confirmed existing research package says `Dataset reviewed: none`.
- Confirmed current local crypto data is fixture/synthetic.
- Confirmed current data service can load manifest-based 7x24 multi-frequency
  data when the manifest is valid.
- Pulled a small Binance Spot REST klines probe for BTCUSDT, ETHUSDT, and
  SOLUSDT over 2026-06-01 to 2026-06-08 UTC for 4h and 1d intervals.
- Probe found no duplicates, no missing expected open slots, and no OHLC or
  volume plausibility failures after accounting for the extra end-boundary row.

## Required Fixes

1. Turn the probe into a reproducible downloader with explicit end-boundary
   handling.
2. Add source metadata, hashes, and quality logs.
3. Decide dataset timestamp semantics: Binance open time vs normalized close
   boundary for engine `dt`.
4. Add cross-source sanity checks.
5. Only then request formal `data-audit-reviewer` review.
