# Task 9 Report

## RED

Command:

```bash
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
```

Output:

```text
==================================== ERRORS ====================================
ImportError while importing test module 'tests/test_alerts_monitor.py'
ModuleNotFoundError: No module named 'quant.live.alerts'
```

## GREEN

```text
.venv/bin/pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
5 passed in 1.24s

.venv/bin/ruff check src/quant/live/alerts.py src/quant/live/monitor.py scripts/ops.py tests/test_alerts_monitor.py tests/test_ops_cli.py
All checks passed!

.venv/bin/pytest -q
70 passed in 1.64s

.venv/bin/lint-imports
Contracts: 1 kept, 0 broken.
```
