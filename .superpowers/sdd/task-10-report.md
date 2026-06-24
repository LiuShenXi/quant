# Task 10 Report: Paper Golden Regression And Runbook

## TDD

- RED: `.venv/bin/pytest tests/test_paper_golden.py -q` failed because `tests/golden_paper/orders.csv` did not exist.
- GREEN: `.venv/bin/pytest tests/test_paper_golden.py -q` passed after generating golden artifacts from `PaperEngine.run_replay(max_bars=20)`.
- Coverage RED: `.venv/bin/python -m pytest tests/test_paper_golden.py -q` failed on
  `assert_has_data_rows(tmp_path / "orders.csv")` because generated paper replay orders were
  header-only.
- Coverage GREEN: `.venv/bin/python -m pytest tests/test_paper_golden.py -q` passed after moving
  the golden replay to `tests.paper_golden_strategy:GoldenPaperStrategy` and regenerating non-empty
  orders/trades/events goldens.

## Golden Generation

- Generated from `.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20`.
- Exported `orders` and `trades` from `runtime/paper/meta.db` using the same deterministic Python SQLite dump helper as the regression test.
- Copied `runtime/paper/events.jsonl` to `tests/golden_paper/events.jsonl`.
- Coverage refresh generated from `PaperEngine.run_replay(max_bars=20)` with a test-only
  `GoldenPaperStrategy` that imports only `quant.core.contract` and queues
  `ctx.set_target("510300.SH", 1000)` once.
- `tests/golden_paper/orders.csv` now includes one filled order row, and
  `tests/golden_paper/trades.csv` now includes one trade row. CSV export uses `csv.writer` with
  deterministic line endings.

## Verification

- `.venv/bin/python -m pytest tests/test_paper_golden.py -q`: 1 passed.
- `.venv/bin/python -m pytest -q`: 77 passed.
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

## Review Fix: M3b Paper Gate Requirements

- Files changed: `README.md`, `docs/runbooks/paper_daily_runbook.md`, `tests/test_paper_runbook_docs.py`.
- RED: `.venv/bin/python -m pytest tests/test_paper_runbook_docs.py -q` was run in a temporary detached worktree at parent commit `94c3721` with the new docs regression test copied in; result: 2 failed. Failures showed `README.md` missing `M3a is deterministic local Paper replay` and the runbook Acceptance Log missing `daily reconciliation zero difference`.
- GREEN: `.venv/bin/python -m pytest tests/test_paper_runbook_docs.py -q`: 2 passed.
- Lint: `.venv/bin/ruff check tests/test_paper_runbook_docs.py`: All checks passed.
- Commit SHA: `187f32bacf2edf4e9016133a654283453c109ad9`.
- Concerns: none.
