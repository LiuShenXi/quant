# Task 4 Report

## RED

Command:

```bash
.venv/bin/pytest tests/test_risk_pipeline.py -q
```

Output:

```text
==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_risk_pipeline.py _________________
ImportError while importing test module '/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m3-paper/tests/test_risk_pipeline.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.13/3.13.3_1/Frameworks/Python.framework/Versions/3.13/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_risk_pipeline.py:6: in <module>
    from quant.risk.pipeline import RiskEngine, RiskLimits
E   ModuleNotFoundError: No module named 'quant.risk.pipeline'
=========================== short test summary info ============================
ERROR tests/test_risk_pipeline.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.69s
```

## Verification

Command:

```bash
.venv/bin/pytest tests/test_risk_pipeline.py tests/test_portfolio_costs.py -q
```

Output:

```text
......                                                                   [100%]
6 passed in 0.65s
```

Command:

```bash
.venv/bin/ruff check src/quant/risk tests/test_risk_pipeline.py
```

Output:

```text
All checks passed!
```

Command:

```bash
.venv/bin/pytest -q
```

Output:

```text
..........................................                               [100%]
42 passed in 0.95s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text
---------
Contracts
---------

Analyzed 18 files, 20 dependencies.
-----------------------------------

core does not depend outward KEPT

Contracts: 1 kept, 0 broken.
```

## Self-Review

- Rule order matches the brief: engine state, whitelist, session, collar, order value, cash/sellable, position, gross exposure, frequency, self-cross.
- `check_order()` catches unexpected exceptions and rejects with `risk_engine_error`.
- Scope stayed limited to paper-risk primitives and the requested report/test files.
