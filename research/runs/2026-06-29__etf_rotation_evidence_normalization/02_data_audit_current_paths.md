# Data Audit - Current Path Normalization

Verdict: `PASS_WITH_WARNINGS`

Dataset reviewed:

`research/imported/usage_records/2026-06-26__quant_usage_record/data/etf_rotation_510300_510500_20250601_20260626`

Intended use:

Research and backtest evidence review through the latest complete bar date
present in `bars_1d.csv`: `2026-06-25T15:00:00+08:00`.

## Blocking Issues

None for research-only review through `2026-06-25`.

## Warnings

- `bars_1d.csv` stops at `2026-06-25T15:00:00+08:00`.
- `trade_calendar.csv` reaches `2026-06-26`.
- This run did not independently refetch provider data.
- The combined dataset build command and log are not yet archived in a complete
  reproducibility package.
- This data audit does not approve paper/live usage.

## Checks Performed

- Loaded bars, calendar, instruments, adjustment factors, orders, trades, and
  equity files with pandas.
- Checked symbol coverage.
- Checked duplicate `(symbol, dt)` rows.
- Checked null counts for OHLCV core fields.
- Checked artifact file presence.
- Reviewed data service semantics in `src/quant/data/service.py`.

## Evidence

```text
symbols=['510300.SH', '510500.SH']
bars_rows=518
bars_min_dt=2025-06-03 15:00:00+08:00
bars_max_dt=2026-06-25 15:00:00+08:00
bars_data_status={'ok': 518}
bars_duplicate_symbol_dt=0
open_nulls=0
high_nulls=0
low_nulls=0
close_nulls=0
volume_nulls=0
amount_nulls=0
calendar_rows=260
calendar_min=2025-06-03
calendar_max=2026-06-26
instrument_rows=2
adjust_factor_rows=518
```

## Hashes

```text
bars_1d.csv
  SHA256=9C34C39BCF02316B916BBEEFB5086BB4E7F66D856FAAC282047A7EF0AB4A48BE
trade_calendar.csv
  SHA256=CD35466665781B22514E9B174D31B054F022D0CACF3103F149206CBFDAC3F625
instruments.csv
  SHA256=D07FCA46644514292551A02B4C06FE6A504EBB04C22C1412BAD199D4E0C4745B
adjust_factors.csv
  SHA256=910B996CDA923F3C39F839E801A1D560CAB3F526CB192738B72033E1EFF7E76B
```

## Required Fixes

- Rebuild or version an extended dataset with matching bars/calendar latest
  dates before paper discussion.
- Archive exact build command, command output, provider version, and file hashes.
- Document whether the latest calendar date is intentionally ahead of available
  bars because data was refreshed before a completed session.
