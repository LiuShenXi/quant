# Task 3 Report: SQLite OMS Store

## What I implemented

- Added `src/quant/live/store.py` with `OmsStore(path: Path)` and `AccountSnapshot`.
- Implemented the required SQLite schema for `orders`, `trades`, `account_snapshots`, `position_snapshots`, `engine_state`, and `kv`.
- Implemented order persistence, order updates, broker order-id mapping, active/all order listing, idempotent trade saves, trade listing, account/position snapshot save/load, engine state save/load, emptiness checks, and JSON key-value persistence.
- Used enum `.value` and `datetime.isoformat()` for writes, with enum constructors and `datetime.fromisoformat()` for reads.
- `save_trade_once()` returns `False` only for duplicate `broker_trade_id` inserts and re-raises other integrity failures.
- `get_engine_state()` returns `EngineState.NORMAL` when no engine-state row exists.

## RED command/output and why it failed as expected

Command:

```bash
.venv/bin/pytest tests/test_live_store.py -q
```

Output:

```text
==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_live_store.py ___________________
ImportError while importing test module '/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m3-paper/tests/test_live_store.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.13/3.13.3_1/Frameworks/Python.framework/Versions/3.13/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_live_store.py:5: in <module>
    from quant.live.store import OmsStore
E   ModuleNotFoundError: No module named 'quant.live.store'
=========================== short test summary info ============================
ERROR tests/test_live_store.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.53s
```

This failed as expected because `tests/test_live_store.py` imported the required `quant.live.store` module before `src/quant/live/store.py` existed.

## GREEN command/output

Command:

```bash
.venv/bin/pytest tests/test_live_store.py -q
```

Output:

```text
...                                                                      [100%]
3 passed in 0.68s
```

Command:

```bash
.venv/bin/ruff check src/quant/live/store.py tests/test_live_store.py
```

Output:

```text
All checks passed!
```

Command:

```bash
.venv/bin/ruff check
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
................................                                         [100%]
32 passed in 0.96s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text
Contracts: 1 kept, 0 broken.
```

## Files changed

- `src/quant/live/store.py`
- `tests/test_live_store.py`
- `.superpowers/sdd/task-3-report.md`

## Self-review findings

- Confirmed the schema matches the task brief table names, columns, primary keys, unique index, and single-row `CHECK (id = 1)` semantics.
- Confirmed enums and timezone-aware datetimes round-trip through SQLite as text.
- Tightened `save_trade_once()` so only duplicate `broker_trade_id` is treated as idempotent; other SQLite integrity failures are not swallowed.
- Confirmed the new `quant.live.store` dependency direction does not break the existing import-linter contract.

## Any concerns

- No blocking concerns.

# Task 3 Review Fix

## What I changed

- Added review-regression tests for missing-order `update_order()` and `map_broker_order_id()` calls raising `KeyError(order_id)`.
- Added a connection-lifetime regression test that verifies per-method SQLite connections are closed.
- Added focused coverage for successful `update_order()`, `list_orders(active_only=True)`, `save_kv()`/`load_kv()`, and unrelated trade integrity errors.
- Updated `OmsStore._connect()` to own transaction handling and close connections in `finally`.
- Updated order update/mapping paths to check `cursor.rowcount` and raise on missing order ids.
- Replaced broker-trade duplicate detection based on SQLite error-message text with `ON CONFLICT(broker_trade_id) DO NOTHING` plus `rowcount`.

## RED command/output and why it failed as expected

Command:

```bash
.venv/bin/pytest tests/test_live_store.py -q
```

Output:

```text
.FFF......                                                               [100%]
=================================== FAILURES ===================================
_______________ test_store_update_order_raises_for_missing_order _______________

tmp_path = PosixPath('/private/var/folders/fb/mvdcfcws0jz4hffbdntzj1fc0000gn/T/pytest-of-shenxi/pytest-35/test_store_update_order_raises0')

    def test_store_update_order_raises_for_missing_order(tmp_path) -> None:
        store = OmsStore(tmp_path / "meta.db")
        store.init_schema()

>       with pytest.raises(KeyError) as exc_info:
             ^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE KeyError

tests/test_live_store.py:53: Failed
___________ test_store_map_broker_order_id_raises_for_missing_order ____________

tmp_path = PosixPath('/private/var/folders/fb/mvdcfcws0jz4hffbdntzj1fc0000gn/T/pytest-of-shenxi/pytest-35/test_store_map_broker_order_id0')

    def test_store_map_broker_order_id_raises_for_missing_order(tmp_path) -> None:
        store = OmsStore(tmp_path / "meta.db")
        store.init_schema()

>       with pytest.raises(KeyError) as exc_info:
             ^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE KeyError

tests/test_live_store.py:63: Failed
_________________ test_store_closes_connections_after_methods __________________

tmp_path = PosixPath('/private/var/folders/fb/mvdcfcws0jz4hffbdntzj1fc0000gn/T/pytest-of-shenxi/pytest-35/test_store_closes_connections_0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x110f03ce0>

    def test_store_closes_connections_after_methods(tmp_path, monkeypatch) -> None:
        real_connect = sqlite3.connect
        connections: list[TrackedConnection] = []

        def connect(*args, **kwargs):
            connection = TrackedConnection(real_connect(*args, **kwargs))
            connections.append(connection)
            return connection

        monkeypatch.setattr(sqlite3, "connect", connect)

        store = OmsStore(tmp_path / "meta.db")
        store.init_schema()
        store.save_order(make_order())
        assert store.get_order("O-1").order_id == "O-1"

        assert connections
>       assert all(connection.closed for connection in connections)
E       assert False
E        +  where False = all(<generator object test_store_closes_connections_after_methods.<locals>.<genexpr> at 0x110eaebc0>)

tests/test_live_store.py:86: AssertionError
=========================== short test summary info ============================
FAILED tests/test_live_store.py::test_store_update_order_raises_for_missing_order
FAILED tests/test_live_store.py::test_store_map_broker_order_id_raises_for_missing_order
FAILED tests/test_live_store.py::test_store_closes_connections_after_methods
3 failed, 7 passed in 0.55s
```

This failed for the expected review findings: missing-order updates/mapping silently succeeded, and the raw SQLite connection context manager did not close the connection.

## GREEN command/output

Command:

```bash
.venv/bin/pytest tests/test_live_store.py -q
```

Output:

```text
..........                                                               [100%]
10 passed in 0.57s
```

Command:

```bash
.venv/bin/ruff check src/quant/live/store.py tests/test_live_store.py
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
.......................................                                  [100%]
39 passed in 0.86s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text
Contracts: 1 kept, 0 broken.
```

## Files changed

- `src/quant/live/store.py`
- `tests/test_live_store.py`
- `.superpowers/sdd/task-3-report.md`

## Self-review findings

- `update_order()` and `map_broker_order_id()` now fail loudly with `KeyError(order_id)` when their `UPDATE` affects no rows.
- `_connect()` preserves one fresh connection per store method and deterministically closes it after commit or rollback.
- `save_trade_once()` returns `False` for duplicate `broker_trade_id` via SQLite conflict handling while still raising unrelated integrity errors.
- Added tests cover both the Important review findings and the straightforward API coverage requested in the minor suggestions.

## Any concerns

- No blocking concerns.
