# Task 9 Review Fix

## Task 9 CLI Output Fix

### RED

Command:

```bash
.venv/bin/pytest tests/test_ops_cli.py -q
```

Output:

```text
.F.                                                                      [100%]
=================================== FAILURES ===================================
__________ test_ops_cli_freeze_open_preserves_halt_and_audits_attempt __________

>       assert freeze_open.stdout.strip() == EngineState.HALT.value
E       AssertionError: assert 'FREEZE_OPEN' == 'HALT'
E
E         - HALT
E         + FREEZE_OPEN

tests/test_ops_cli.py:109: AssertionError
=========================== short test summary info ============================
FAILED tests/test_ops_cli.py::test_ops_cli_freeze_open_preserves_halt_and_audits_attempt
1 failed, 2 passed in 1.49s
```

### GREEN

Commands:

```bash
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
.venv/bin/ruff check scripts/ops.py tests/test_ops_cli.py
.venv/bin/pytest -q
.venv/bin/lint-imports
```

Output:

```text
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
...........                                                              [100%]
11 passed in 1.49s

.venv/bin/ruff check scripts/ops.py tests/test_ops_cli.py
All checks passed!

.venv/bin/pytest -q
........................................................................ [ 94%]
....                                                                     [100%]
76 passed in 1.77s

.venv/bin/lint-imports
Analyzed 18 files, 20 dependencies.
Contracts: 1 kept, 0 broken.
```

## RED

Command:

```bash
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
```

Output:

```text
..F....F.F.                                                              [100%]
=================================== FAILURES ===================================
_______________ test_crit_alert_rejects_unusable_required_fields _______________
E               AssertionError: CRIT alert accepted unusable 'run_id'

_________________ test_halt_survives_disconnect_and_reconnect __________________
E       AssertionError: assert <EngineState.NORMAL: 'NORMAL'> == <EngineState.HALT: 'HALT'>

__________ test_ops_cli_freeze_open_preserves_halt_and_audits_attempt __________
E       AssertionError: assert <EngineState.FREEZE_OPEN: 'FREEZE_OPEN'> == <EngineState.HALT: 'HALT'>

3 failed, 8 passed in 1.67s
```

## GREEN

Commands:

```bash
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
.venv/bin/ruff check src/quant/live/alerts.py src/quant/live/monitor.py scripts/ops.py tests/test_alerts_monitor.py tests/test_ops_cli.py
.venv/bin/pytest -q
.venv/bin/lint-imports
```

Output:

```text
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
11 passed in 1.26s

.venv/bin/ruff check src/quant/live/alerts.py src/quant/live/monitor.py scripts/ops.py tests/test_alerts_monitor.py tests/test_ops_cli.py
All checks passed!

.venv/bin/pytest -q
76 passed in 1.88s

.venv/bin/lint-imports
Contracts: 1 kept, 0 broken.
```
