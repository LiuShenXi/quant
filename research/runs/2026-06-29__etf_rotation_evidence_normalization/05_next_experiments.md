# Next Experiments - ETF Regime Rotation v1

Status: `READY_FOR_RESEARCH_EXECUTION`

## Priority 1 - Reproducible Extended Dataset

Status: `BLOCKED_BY_DATA_DEPENDENCY`

Goal:

Build or obtain a longer reproducible daily ETF dataset for `510300.SH` and
`510500.SH`.

Required evidence:

- build command
- provider/source and retrieval date
- provider version where available
- row counts
- bars/calendar latest-date alignment
- file hashes
- data audit note

Failure condition:

If the dataset cannot be reproduced or source lineage is unclear, keep the
strategy research-only and do not run new claims from it.

Current blocker:

- active Python environment has `pandas` but not `akshare`
- `python -m pip install "akshare>=1.18"` failed with SSL EOF errors
- retry with trusted hosts failed with proxy connection errors
- no partial long-history dataset was created

Required next action:

- fix Python package/proxy access or provide a local `akshare` wheel
- re-run the long-history build
- perform data audit before any long-history backtest claim

## Priority 2 - Benchmark Robustness

Status: `COMPLETE_FOR_CURRENT_WINDOW`

Goal:

Decide whether ETF rotation has a durable drawdown-controlled participation
benefit after opportunity cost.

Benchmarks:

- `510300.SH` buy-and-hold
- `510500.SH` buy-and-hold
- equal-weight `510300.SH`/`510500.SH`
- cash/risk-off baseline

Required metrics:

- return
- max drawdown
- volatility
- turnover
- trade count
- commission and slippage
- exposure time

Failure condition:

If the strategy consistently gives up too much return for a small or unstable
drawdown improvement, retire or downgrade the thesis.

Current-window result:

- `etf_regime_rotation_v1`: 20.0983% return, -6.4892% max drawdown
- `510300.SH` buy-and-hold: 27.5714% return, -9.9410% max drawdown
- `510500.SH` buy-and-hold: 59.3021% return, -14.0208% max drawdown
- normalized equal-weight hold: 43.4368% return, -10.7071% max drawdown

Next benchmark gap:

- longer-history benchmark comparison
- sample-split benchmark comparison
- cost-aware benchmark comparison if benchmark portfolios are made tradeable

## Priority 3 - Sensitivity Tests

Parameters to vary:

- `trend_window`
- `momentum_window`
- `score_buffer`
- `min_hold_days`
- cost/slippage assumptions
- one-day delayed execution

Rule:

Do not select the best parameter set as a trading recommendation. Use
sensitivity only to test whether the thesis is fragile.

## Priority 3a - Sample Split

Status: `COMPLETE_FOR_CURRENT_WINDOW`

Current split evidence:

- first half: strategy returned 1.3941%, while equal-weight returned 23.6013%
- second half: strategy returned 18.9313%, while equal-weight returned 16.4916%
- strategy return is concentrated in the second half

Required next check:

- repeat the same split logic on longer history once data is available

## Priority 4 - Full Report and Repo-Level Inspector

Status: `PARTIALLY_COMPLETE`

Create a deterministic report or inspection script that summarizes:

- required files present
- rows and date ranges
- initial/final value
- return and drawdown
- trade count
- rejected orders
- cost summary
- benchmark comparison
- config snapshot path
- artifact hashes

The repo-level artifact completeness inspector now exists at
`scripts/inspect_backtest_artifacts.py`.

The repo-level core metrics report generator now exists at
`scripts/report_backtest_artifacts.py`.

Remaining gap:

- preserve report outputs under each research run
- add longer-history summaries
