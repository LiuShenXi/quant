# Benchmark Report Enablement

Status: `COMPLETE_FOR_CURRENT_DATASET`

## Change

Added a repository-level deterministic benchmark report:

```text
scripts/report_backtest_benchmarks.py
```

## Method

The report uses `close_to_close_normalized_buy_and_hold`:

- each single-symbol benchmark starts at normalized equity 100000
- each benchmark holds from the first close to the last close
- equal-weight benchmark averages normalized close-relative equity curves across
  the requested symbols

This definition is intentionally explicit because older notes used a less
precise "equal-weight close index" phrasing.

## Evidence Generated

```text
artifacts/benchmark_etf_rotation_dataset.json
```

Current benchmark results:

| Benchmark | Return | Max drawdown |
| --- | ---: | ---: |
| `510300.SH` buy-and-hold | 27.5714% | -9.9410% |
| `510500.SH` buy-and-hold | 59.3021% | -14.0208% |
| normalized equal-weight hold | 43.4368% | -10.7071% |
| `etf_regime_rotation_v1` backtest | 20.0983% | -6.4892% |

## Interpretation

ETF rotation underperformed all three simple hold benchmarks on absolute return
in this window, but had lower max drawdown. This supports the current narrowed
thesis: drawdown-controlled participation, not proven absolute-return alpha.

## Remaining Gap

This is same-window benchmark evidence only. The next required research step is
sample-split and longer-history robustness. No paper/live decision can be made
from this benchmark report.

