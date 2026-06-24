# Task 9 Review Fix

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
