# Sample-Split Report Enablement

Status: `COMPLETE_FOR_CURRENT_DATASET`

## Change

Added a repository-level deterministic sample-split report:

```text
scripts/report_backtest_sample_splits.py
```

## Method

The report uses `unique_date_halves_daily_last_equity`:

- collapse strategy `equity.csv` to one row per trading date by taking the last
  equity row for that date
- split unique dates into first half and second half
- compute strategy return and max drawdown within each half
- compute close-to-close normalized buy-and-hold benchmarks within each half

## Evidence Generated

```text
artifacts/sample_split_etf_rotation_dataset.json
```

Current sample-split results:

| Split | Strategy return | Strategy max DD | Equal-weight return | 510300 return | 510500 return |
| --- | ---: | ---: | ---: | ---: | ---: |
| first half | 1.3941% | -5.7348% | 23.6013% | 19.5855% | 27.6170% |
| second half | 18.9313% | -6.4892% | 16.4916% | 7.2218% | 25.7614% |

## Interpretation

The strategy's return is not stable across the two halves. Most of the return
appears in the second half. It underperforms all same-split benchmarks in the
first half, beats `510300.SH` and equal-weight in the second half, and still
underperforms `510500.SH` in the second half.

This supports `HOLD_FOR_ROBUSTNESS`, not paper progression.

## Remaining Gap

The next required evidence is longer-history robustness. A one-year split is
too short to decide whether the lower-drawdown behavior is durable.

