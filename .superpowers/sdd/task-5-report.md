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

## Task 5 Snapshot Persist Fix

### RED

Command:

```bash
.venv/bin/pytest tests/test_oms.py -q
```

Output:

```text
.......F..                                                               [100%]
=================================== FAILURES ===================================
_____ test_trade_snapshot_persist_failure_freezes_open_and_audits_failure ______

tmp_path = PosixPath('/private/var/folders/fb/mvdcfcws0jz4hffbdntzj1fc0000gn/T/pytest-of-shenxi/pytest-60/test_trade_snapshot_persist_fa0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x115321350>

    def test_trade_snapshot_persist_failure_freezes_open_and_audits_failure(
        tmp_path,
        monkeypatch,
    ) -> None:
        manager = make_manager(tmp_path)
        order_id = submit_known_order(manager)
        snap = make_trade_snapshot(order_id)
    
        def fail_snapshot_save(*args, **kwargs) -> None:
            raise RuntimeError("snapshot db offline")
    
        monkeypatch.setattr(manager.store, "save_account_snapshot", fail_snapshot_save)
    
        with pytest.raises(RuntimeError, match="snapshot db offline"):
            manager.on_broker_trade(snap)
    
        assert len(manager.store.list_trades()) == 1
>       assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
E       AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState....'FREEZE_OPEN'>
E         
E         - FREEZE_OPEN
E         + NORMAL

tests/test_oms.py:281: AssertionError
=========================== short test summary info ============================
FAILED tests/test_oms.py::test_trade_snapshot_persist_failure_freezes_open_and_audits_failure
1 failed, 9 passed in 0.53s
```

### Verification

Command:

```bash
.venv/bin/pytest tests/test_oms.py tests/test_live_store.py tests/test_risk_pipeline.py -q
```

Output:

```text
.......................                                                  [100%]
23 passed in 0.59s
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
....................................................                     [100%]
52 passed in 1.10s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘


---------
Contracts
---------

Analyzed 18 files, 20 dependencies.
-----------------------------------

core does not depend outward KEPT

Contracts: 1 kept, 0 broken.
```

## Task 5 HALT Preservation Fix

### RED

Command:

```bash
.venv/bin/pytest tests/test_oms.py -q
```

Output:

```text
.....F...                                                                [100%]
=================================== FAILURES ===================================
_________ test_freeze_open_preserves_existing_halt_and_audits_attempt __________

tmp_path = PosixPath('/private/var/folders/fb/mvdcfcws0jz4hffbdntzj1fc0000gn/T/pytest-of-shenxi/pytest-55/test_freeze_open_preserves_exi0')

    def test_freeze_open_preserves_existing_halt_and_audits_attempt(tmp_path) -> None:
        manager = make_manager(tmp_path)
    
        manager.halt("manual halt")
        manager.freeze_open("gateway issue")
    
>       assert manager.store.get_engine_state() == EngineState.HALT
E       AssertionError: assert <EngineState....'FREEZE_OPEN'> == <EngineState.HALT: 'HALT'>
E         
E         - HALT
E         + FREEZE_OPEN

tests/test_oms.py:228: AssertionError
=========================== short test summary info ============================
FAILED tests/test_oms.py::test_freeze_open_preserves_existing_halt_and_audits_attempt
1 failed, 8 passed in 0.57s
```

### Verification

Command:

```bash
.venv/bin/pytest tests/test_oms.py tests/test_live_store.py tests/test_risk_pipeline.py -q
```

Output:

```text
......................                                                   [100%]
22 passed in 0.52s
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
...................................................                      [100%]
51 passed in 0.64s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘


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

## Task 5 Review Fix

### RED

Command:

```bash
.venv/bin/pytest tests/test_oms.py -q
```

Output:

```text
...FFFF.                                                                 [100%]
=================================== FAILURES ===================================
______ test_unknown_broker_order_halts_and_audits_reconciliation_failure _______

    with pytest.raises(KeyError, match="O-404"):
        manager.on_broker_order(snap)

>   assert manager.store.get_engine_state() == EngineState.HALT
E   AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState.HALT: 'HALT'>

tests/test_oms.py:185: AssertionError
__________ test_unknown_broker_trade_halts_and_does_not_persist_trade __________

>   with pytest.raises(KeyError, match="O-404"):
E   Failed: DID NOT RAISE KeyError

tests/test_oms.py:203: Failed
_______ test_trade_gateway_query_failure_freezes_open_and_audits_failure _______

    assert len(manager.store.list_trades()) == 1
>   assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
E   AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState....'FREEZE_OPEN'>

tests/test_oms.py:232: AssertionError
____________ test_cancel_failure_records_manual_op_and_freezes_open ____________

    assert manager.gateway.cancelled == ["PAPER-O-1"]
>   assert manager.store.get_engine_state() == EngineState.FREEZE_OPEN
E   AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState....'FREEZE_OPEN'>

tests/test_oms.py:256: AssertionError
=========================== short test summary info ============================
FAILED tests/test_oms.py::test_unknown_broker_order_halts_and_audits_reconciliation_failure
FAILED tests/test_oms.py::test_unknown_broker_trade_halts_and_does_not_persist_trade
FAILED tests/test_oms.py::test_trade_gateway_query_failure_freezes_open_and_audits_failure
FAILED tests/test_oms.py::test_cancel_failure_records_manual_op_and_freezes_open
4 failed, 4 passed in 0.61s
```

### Verification

Command:

```bash
.venv/bin/pytest tests/test_oms.py tests/test_live_store.py tests/test_risk_pipeline.py -q
```

Output:

```text
.....................                                                    [100%]
21 passed in 0.57s
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
..................................................                       [100%]
50 passed in 0.98s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲
      ╚╝────────────────────┘


---------
Contracts
---------

Analyzed 18 files, 20 dependencies.
-----------------------------------

core does not depend outward KEPT

Contracts: 1 kept, 0 broken.
```
