# Data Audit - ETF Regime Rotation v1

Verdict:

`PASS_WITH_WARNINGS`

Dataset reviewed:

- Path: `量化使用记录2026-06-26/data/etf_rotation_510300_510500_20250601_20260626`
- Files: `bars_1d.csv`, `trade_calendar.csv`, `instruments.csv`, `adjust_factors.csv`
- Provider/source recorded in bars: `akshare:fund_etf_hist_sina`
- Asset universe: `510300.SH`, `510500.SH`
- Intended use: research/backtest review only, not paper/live

Intended use:

The dataset may be used for research and backtest evidence review through the latest complete bar date present in `bars_1d.csv`: `2026-06-25T15:00:00+08:00`. It must not be described as a complete `2026-06-26` dataset without rebuilding or documenting the missing bars.

Blocking issues:

None for research/backtest review through `2026-06-25`.

Warnings:

- The trade calendar contains 260 open days from `2025-06-03` through `2026-06-26`, but both ETF bar series contain 259 rows and stop at `2026-06-25`.
- Each symbol is missing `2026-06-26` relative to the included calendar.
- The inspected build logs for the single-ETF datasets show `bars: 259` and `calendar days: 260`; this supports the mismatch finding but does not fully document a combined rotation dataset build command.
- Backtest logs for ETF rotation are empty, so command provenance depends on config snapshots and artifact inspection rather than a detailed run log.
- The source is named, but this review did not independently re-fetch or compare provider data from the internet.

Checks performed:

- Loaded all four required CSV tables with pandas.
- Verified symbols present in `bars_1d.csv`.
- Counted open trade-calendar days.
- Compared per-symbol bar dates against calendar dates.
- Checked duplicate `(symbol, dt)` rows.
- Checked non-positive and internally implausible OHLC values.
- Checked negative volume/amount values.
- Checked `data_status` counts.
- Checked adjustment-factor row counts and non-positive factors.
- Checked instrument rows and symbol coverage.
- Reviewed data service and AKShare ETF builder code for expected table semantics.

Evidence:

```text
bars_rows=518
calendar_open_days=260
calendar_first=2025-06-03
calendar_last=2026-06-26
symbols=['510300.SH', '510500.SH']

510300.SH:
  rows=259
  first_dt=2025-06-03 15:00:00+08:00
  last_dt=2026-06-25 15:00:00+08:00
  missing_count=1
  missing_sample=[2026-06-26]
  duplicates=0
  bad_ohlc=0
  bad_volume=0
  data_status={'ok': 259}

510500.SH:
  rows=259
  first_dt=2025-06-03 15:00:00+08:00
  last_dt=2026-06-25 15:00:00+08:00
  missing_count=1
  missing_sample=[2026-06-26]
  duplicates=0
  bad_ohlc=0
  bad_volume=0
  data_status={'ok': 259}

adjust_factors:
  510300.SH rows=259, first=2025-06-03, last=2026-06-25, non_positive=0
  510500.SH rows=259, first=2025-06-03, last=2026-06-25, non_positive=0

instruments_rows=2
instrument_symbols=['510300.SH', '510500.SH']
source=['akshare:fund_etf_hist_sina']
```

Required fixes:

- Before any paper discussion, rebuild or explicitly version a dataset whose bars and calendar have matching latest dates.
- Archive the exact build command and output log for the combined rotation dataset.
- Preserve data hashes for `bars_1d.csv`, `trade_calendar.csv`, `instruments.csv`, and `adjust_factors.csv`.
- If the strategy depends on same-day bars, document the post-close availability rule and confirm no row after `ctx.now` can enter a decision.

Next decision:

Proceed to `backtest-validator` for the existing ETF rotation backtest artifacts, limited to the dataset ending `2026-06-25`. Do not promote to paper from this data audit alone.

