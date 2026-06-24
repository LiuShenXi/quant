# M3 Task 8 Paper Engine And Strategy Context Report

## Red run

Command:

```bash
.venv/bin/pytest tests/test_paper_engine.py -q
```

Output:

```text
E   ModuleNotFoundError: No module named 'quant.live.engine'
```

## Green run

Command:

```bash
.venv/bin/pytest tests/test_paper_engine.py -q
```

Output:

```text
4 passed in 0.62s
```

## Final verification

Command:

```bash
.venv/bin/pytest tests/test_paper_engine.py tests/test_oms.py tests/test_sim_gateway.py -q
```

Output:

```text
19 passed in 0.62s
```

Command:

```bash
.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
```

Output:

```text
paper events: runtime/paper/events.jsonl
paper store: runtime/paper/meta.db
final state: NORMAL
```

Command:

```bash
.venv/bin/ruff check src/quant/data/service.py src/quant/live/context.py src/quant/live/engine.py src/quant/live/execution.py scripts/run_paper.py tests/test_paper_engine.py
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
65 passed in 0.88s
```

Command:

```bash
.venv/bin/lint-imports
```

Output:

```text
Contracts: 1 kept, 0 broken.
```
