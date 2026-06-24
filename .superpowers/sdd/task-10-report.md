# Task 10 Report: Paper Golden Regression And Runbook

## TDD

- RED: `.venv/bin/pytest tests/test_paper_golden.py -q` failed because `tests/golden_paper/orders.csv` did not exist.
- GREEN: `.venv/bin/pytest tests/test_paper_golden.py -q` passed after generating golden artifacts from `PaperEngine.run_replay(max_bars=20)`.

## Golden Generation

- Generated from `.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20`.
- Exported `orders` and `trades` from `runtime/paper/meta.db` using the same deterministic Python SQLite dump helper as the regression test.
- Copied `runtime/paper/events.jsonl` to `tests/golden_paper/events.jsonl`.

## Verification

- `.venv/bin/pytest tests/test_paper_golden.py -q`: 1 passed.
- `.venv/bin/pytest -q`: 77 passed.
- `.venv/bin/ruff check .`: All checks passed.
- `.venv/bin/lint-imports`: Contracts: 1 kept, 0 broken.
- `.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20`: final state `NORMAL`.
- `.venv/bin/python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status`: `NORMAL`.

## Self-Review

- Golden determinism: regression uses `tmp_path` and byte-compares CSV and JSONL artifacts; golden event `written_at` values are simulated bar-clock timestamps (`2024-01-02T15:00:00+08:00`), not wall-clock times.
- Runbook completeness: covers pre-open checks, runtime alerts/state handling, close/archive steps, and 10-day acceptance logging.
- README wording: states M3 is paper infrastructure only and excludes QMT, real broker gateways, and real-money trading.
- Runtime ignored: `runtime/` remains ignored by `.gitignore`; verification runtime state is not staged.
- Real broker scope: no QMT, real broker, or live-money code paths were added.
