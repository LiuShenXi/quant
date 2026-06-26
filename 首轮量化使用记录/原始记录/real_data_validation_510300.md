# 510300 Real-Data Validation

Date: 2026-06-26

## Purpose

Start the non-money validation phase with a narrow, real A-share ETF slice before adding
more symbols or broker connectivity.

This is not an M3b sign-off package. It is the first real-data plumbing and strategy
candidate record.

## Data Decision

Initial symbol: `510300.SH` / 沪深300ETF.

Reasons:

- Large, liquid A-share ETF with simple lot size and T+1 semantics.
- Avoids the first wave of individual-stock problems: delisting, long suspensions,
  ST rules, corporate-action edge cases, and universe membership drift.
- Suitable for validating the existing daily-bar backtest and Paper infrastructure.

Data sources considered:

- `thuquant/awesome-quant`: useful index of quant resources, not a data source itself.
- AkShare `fund_etf_hist_em`: preferred when available because it can provide Eastmoney
  ETF daily bars and qfq bars, but this environment repeatedly hit Eastmoney connection
  failures through the local/system network path.
- AkShare `fund_etf_hist_sina`: used for the first dataset because it returned stable
  historical ETF bars for `sh510300`.
- TuShare: planned as the second-source cross-check once a token and quota are available.
- QMT `xtdata`: deferred to M4; do not use it as a blocker for this non-money phase.

Generated local data root:

```text
data_real/etf_510300_2023_2024/
```

Generated files:

```text
bars_1d.csv
instruments.csv
adjust_factors.csv
trade_calendar.csv
```

Important limitations:

- The committed repo ignores `data_real/`; regenerate locally when needed.
- If Eastmoney qfq bars are unavailable, the Sina fallback now uses
  `fund_etf_dividend_sina` cumulative dividends to synthesize qfq close factors. The raw
  bars remain unadjusted on disk. Exact exchange limit prices and explicit suspension
  rows are still not provided by this fallback; limit prices are approximated as previous
  close ±10%.
- Before M3b day-counting, manually cross-check at least 10 random dates against a broker
  terminal or another source.

## 2025-2026 Manual Check Against User Screenshot

The user checked a local行情软件 K-line tooltip for `510300` on `2025-06-19`.

Screenshot values, with the software set to 前复权:

```text
open  3.775
high  3.776
low   3.740
close 3.750
amount 23.31 亿
```

Raw vendor bar generated locally:

```text
open  3.898
high  3.899
low   3.863
close 3.873
amount 23.31 亿
```

Dividend check:

```text
fund_etf_dividend_sina("sh510300")
2025-06-18 cumulative dividend: 0.757
2026-01-19 cumulative dividend: 0.880
future adjustment from 2025-06-19 to current end: 0.123
```

Therefore:

```text
3.898 - 0.123 = 3.775
3.899 - 0.123 = 3.776
3.863 - 0.123 = 3.740
3.873 - 0.123 = 3.750
```

The human screenshot and local data match after qfq adjustment.

Recent generated local data root:

```text
data_real/etf_510300_2025_2026_check/
```

Recent Paper config now points at that data root:

```text
config/paper_real_510300.yaml
```

Recent 20/60 real-validation backtest:

- Output: `results/real_510300_2025_2026_ma20_60/`
- Final value: `97427.57`
- 6 filled trades.

Recent 20/60 real-validation Paper replay:

- Final state: `NORMAL`
- Ops status: `NORMAL`
- SQLite store: 5 orders, 5 trades, 0 active orders.

Recent 20/60 disconnect drill:

- Final state: `NORMAL`
- Drill reconciliation status: `OK`

## Commands Run

Build data:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from pathlib import Path
from quant.data.akshare_etf import fetch_etf_dataset, write_dataset

dataset = fetch_etf_dataset(
    symbol="510300.SH",
    name="沪深300ETF",
    start_date="20230101",
    end_date="20241231",
    retries=1,
)
write_dataset(dataset, Path("data_real/etf_510300_2023_2024"))
PY
```

Smoke backtest, existing fast sample config:

```bash
.venv/bin/python scripts/run_backtest.py \
  --strategy config/strategies/dual_ma_510300.yaml \
  --data-root data_real/etf_510300_2023_2024 \
  --out results/real_510300_2023_2024
```

Candidate backtest, slower real-validation config:

```bash
.venv/bin/python scripts/run_backtest.py \
  --strategy config/strategies/dual_ma_510300_real_validation.yaml \
  --data-root data_real/etf_510300_2023_2024 \
  --out results/real_510300_2023_2024_ma20_60
```

Candidate Paper replay:

```bash
rm -rf runtime/paper_real_510300
.venv/bin/python scripts/run_paper.py \
  --strategy config/strategies/dual_ma_510300_real_validation_paper.yaml \
  --paper config/paper_real_510300.yaml \
  --risk config/risk/global.yaml
```

Candidate disconnect drill:

```bash
rm -rf runtime/paper_real_510300
.venv/bin/python scripts/run_paper.py \
  --strategy config/strategies/dual_ma_510300_real_validation_paper.yaml \
  --paper config/paper_real_510300.yaml \
  --risk config/risk/global.yaml \
  --max-bars 80 \
  --disconnect-drill \
  --disconnect-reason "real validation strategy drill"
```

## Observed Results

Dataset:

- 484 daily bars from `2023-01-03T15:00:00+08:00` to
  `2024-12-31T15:00:00+08:00`.
- Source stored in bars: `akshare:fund_etf_hist_sina`.

Existing 3/5 sample backtest:

- Final value: `103496.19`.
- Output artifacts written under `results/real_510300_2023_2024/`.

20/60 real-validation backtest:

- Final value: `96441.91`.
- 8 filled trades and one final submitted order in backtest output.
- Output artifacts written under `results/real_510300_2023_2024_ma20_60/`.

20/60 real-validation Paper replay:

- Final state: `NORMAL`.
- Ops status: `NORMAL`.
- Event journal: 51 events.
- SQLite store: 8 orders, 8 trades, 0 active orders.
- Close reconciliation: `OK`, `cash_diff: 0.0`, no position diffs.

20/60 disconnect drill:

- Final state: `NORMAL`.
- Drill reconciliation status: `OK`.

## Strategy Candidate

Use `DualMA` as a first non-money validation strategy with conservative daily parameters:

```text
symbol: 510300.SH
fast: 20
slow: 60
target_qty: 10000
initial_cash: 100000
```

This strategy is not selected because the initial return is attractive. It is selected
because it is simple, sparse, inspectable, and exercises the full Paper path without
creating excessive churn.

Operational rule: during the validation phase, Paper replay and daily Paper evidence are
the authority. Backtest output is only a data and artifact smoke test because the current
backtest and Paper loops intentionally have different timing models.

## Next Data Expansion

After the 510300 path is repeatable:

1. Add a second-source check for 510300, preferably TuShare or a broker export.
2. Add one more broad ETF, such as `510500.SH`, to test multi-symbol data handling.
3. Add one growth ETF, such as `159915.SZ`, only after Shenzhen ETF symbol handling is
   verified.
4. Do not add individual stocks until data quality checks cover missing rows, suspensions,
   and corporate-action edge cases.

## Entry Criteria Before Formal M3b Counting

- Regenerate data for the intended observation window.
- Manually cross-check at least 10 random bars against an independent source.
- Run `pytest -q`, `ruff check .`, and `lint-imports`.
- Run normal Paper replay and disconnect-drill Paper replay on the selected config.
- Archive the generated data root, `runtime/paper_real_510300/meta.db`, and
  `runtime/paper_real_510300/events.jsonl` for the dry-run evidence package.
