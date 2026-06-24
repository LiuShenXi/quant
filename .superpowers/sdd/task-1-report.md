# M3 Task 1 Report: Paper Configuration And Live Package Skeleton

## What I implemented

- Extended `StrategyConfig` runtime mode support from `backtest` to `backtest | paper`.
- Added the new `quant.live` package with `PaperConfig`, `ReconciliationConfig`, `MonitorConfig`, and `load_paper_config(path: Path) -> PaperConfig`.
- Created the paper runtime config fixtures:
  - `config/paper.yaml`
  - `config/risk/global.yaml`
  - `config/strategies/dual_ma_510300_paper.yaml`
- Added `tests/test_live_config.py` to cover paper strategy loading and paper runtime config parsing.

## RED

Command:

```bash
.venv/bin/pytest tests/test_live_config.py -q
```

Output:

```text
==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_live_config.py __________________
ImportError while importing test module '/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m3-paper/tests/test_live_config.py'.
...
E   ModuleNotFoundError: No module named 'quant.live'
```

Why it failed as expected:

- The test imported `quant.live.config`, but the `quant.live` package did not exist yet.
- That confirmed the test was exercising the missing paper-runtime surface the task asked for.

## GREEN

Commands:

```bash
.venv/bin/pytest tests/test_live_config.py -q
.venv/bin/ruff check src/quant/core/config.py src/quant/live/config.py tests/test_live_config.py
.venv/bin/lint-imports
.venv/bin/pytest -q
```

Outputs:

```text
2 passed in 0.07s
```

```text
All checks passed!
```

```text
Contracts: 1 kept, 0 broken.
```

```text
26 passed in 0.82s
```

## Files changed

- `src/quant/core/config.py`
- `src/quant/live/__init__.py`
- `src/quant/live/config.py`
- `config/paper.yaml`
- `config/risk/global.yaml`
- `config/strategies/dual_ma_510300_paper.yaml`
- `tests/test_live_config.py`

## Self-review findings

- The new paper config loader uses the existing `load_yaml` helper, so it stays aligned with the repo’s config parsing pattern.
- `StrategyConfig` still keeps the existing validators for `universe` and `params`.
- The new `PaperConfig` fields accept the paths and thresholds asserted by the test, and the defaults are explicit.
- `ruff`, `lint-imports`, and the full test suite all passed after the change.

## Concerns

- None for this task. The paper runtime skeleton is in place and the current tests are green.

---

# Fix report: typed global risk config

## What I changed

- Added `KillSwitchConfig` and `GlobalRiskConfig` to `src/quant/live/config.py`.
- Added `load_global_risk_config(path: Path) -> GlobalRiskConfig`.
- Extended `tests/test_live_config.py` to load `config/risk/global.yaml` and assert representative fields.

## RED

Command:

```bash
.venv/bin/pytest tests/test_live_config.py -q
```

Output:

```text
==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_live_config.py __________________
ImportError while importing test module '/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m3-paper/tests/test_live_config.py'.
...
E   ImportError: cannot import name 'load_global_risk_config' from 'quant.live.config'
```

## GREEN

Commands:

```bash
.venv/bin/pytest tests/test_live_config.py -q
.venv/bin/ruff check src/quant/live/config.py tests/test_live_config.py
.venv/bin/lint-imports
.venv/bin/pytest -q
```

Outputs:

```text
3 passed in 0.08s
```

```text
All checks passed!
```

```text
Contracts: 1 kept, 0 broken.
```

```text
27 passed in 0.76s
```
