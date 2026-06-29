# Longer-History Data Probe

Verdict: `FAIL`

## Objective

Probe whether the current environment can build a longer ETF daily dataset for
`510300.SH` and `510500.SH`, starting with `510300.SH` from `2020-01-01` through
`2026-06-26`.

This is a data-readiness check, not a strategy result.

## Commands Run

```powershell
python scripts\check_data_dependencies.py --module pandas --module akshare
python scripts\build_akshare_etf_data.py --symbol 510300.SH --name 300ETF --start-date 20200101 --end-date 20260626 --out research\datasets\probe_510300_20200101_20260626
python -m pip install "akshare>=1.18"
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "akshare>=1.18"
```

## Evidence

Dependency probe:

```text
pandas available: true
akshare available: false
status: FAIL
```

Build result:

```text
RuntimeError: akshare is required for fetching real ETF data; install the data extra first
```

Install attempts:

```text
python -m pip install "akshare>=1.18"
```

failed with SSL EOF errors when reaching PyPI.

```text
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "akshare>=1.18"
```

failed with proxy connection errors.

## Data Workspace State

No partial long-history dataset was created. `research/datasets/` still only
contains `.gitkeep`.

## Data Audit Conclusion

Verdict: `FAIL`

Dataset reviewed:

No longer-history dataset exists yet.

Intended use:

Longer-history robustness research for `etf_regime_rotation_v1`.

Blocking issues:

- `akshare` is not installed in the active Python environment.
- The project declares `akshare>=1.18` under the `data` optional dependency, but
  this environment cannot currently install it from PyPI.
- Without the provider dependency, the long-history dataset cannot be built,
  audited, or used for backtest claims.

Warnings:

- This is an environment/dependency blocker, not evidence that provider data is
  unavailable.
- Existing one-year data remains usable only under its prior `PASS_WITH_WARNINGS`
  research scope.

Required fixes:

- Restore Python package installation path, proxy, or local wheel access.
- Install the project data extra or `akshare>=1.18`.
- Re-run the dataset build and then perform a full data audit before any
  longer-history backtest claim.

## Next Decision

`HOLD_FOR_ROBUSTNESS`. Keep ETF rotation research-only. Do not infer
longer-history robustness from the current one-year dataset.

