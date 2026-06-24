# Task 5 Report

## RED

Command:

```bash
.venv/bin/pytest tests/test_oms.py -q
```

Output:

```text
==================================== ERRORS ====================================
______________________ ERROR collecting tests/test_oms.py ______________________
ImportError while importing test module '/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m3-paper/tests/test_oms.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.13/3.13.3_1/Frameworks/Python.framework/Versions/3.13/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_oms.py:6: in <module>
    from quant.live.oms import OrderManager
E   ModuleNotFoundError: No module named 'quant.live.oms'
=========================== short test summary info ============================
ERROR tests/test_oms.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.53s
```

Additional RED cycle for global failure semantics:

Command:

```bash
.venv/bin/pytest tests/test_oms.py::test_risk_engine_exception_freezes_open_without_gateway_send -q
```

Output:

```text
F                                                                        [100%]
=================================== FAILURES ===================================
_________ test_risk_engine_exception_freezes_open_without_gateway_send _________

    assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
E   AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState....'FREEZE_OPEN'>

tests/test_oms.py:109: AssertionError
=========================== short test summary info ============================
FAILED tests/test_oms.py::test_risk_engine_exception_freezes_open_without_gateway_send
1 failed in 0.88s
```

## Verification

Command:

```bash
.venv/bin/pytest tests/test_oms.py tests/test_live_store.py tests/test_risk_pipeline.py -q
```

Output:

```text
.................                                                        [100%]
17 passed in 0.55s
```

Command:

```bash
.venv/bin/ruff check src/quant/live/oms.py tests/test_oms.py
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
..............................................                           [100%]
46 passed in 1.17s
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

- Persistence before send: allowed orders are saved as `SUBMITTING` before `gateway.send_order()`; risk rejects are saved as `REJECTED` and never sent.
- Event audit coverage: OMS appends JSONL events for orders, risk rejects, trades, broker-order reconciliation, engine-state transitions, and manual cancel operations.
- Idempotent trade handling: `on_broker_trade()` uses `save_trade_once()` and returns `None` for duplicate broker trade IDs without appending another trade event.
- Failure semantics and scope: `risk_engine_error` and gateway query/send failures reject the local order, avoid gateway sends when applicable, and freeze opening orders; implementation stays paper-only with no real broker/QMT path.
