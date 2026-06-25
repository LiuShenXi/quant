# Task 1 Report: M4-0 Evidence And Secrets Gate

## What I Implemented

- Hardened `validate_m3b_signoff(...)` to require and load `event_journal_path` and `trade_calendar_path`.
- Added trade-calendar membership validation and strictly increasing `trading_days` dates.
- Added `counted_window` validation with at least 10 counted trading days while allowing extra observation days in the evidence.
- Added JSONL event-journal indexing by `seq`, duplicate journal seq detection, and referenced event seq existence checks.
- Added semantic checks for referenced startup/close reconciliation, disconnect drill, recovery, and CRIT alert delivery events:
  - expected event `type`
  - event date from `written_at`
  - `payload.status` and `payload.startup` for reconciliation
  - `run_id`, `strategy_id`, and `account_id`
  - CRIT `payload.severity` and `payload.delivery_id`
- Extended `docs/runbooks/m3b_signoff_template.yaml` with journal/calendar paths, counted window, context fields, drill date/reason, and CRIT severity.
- Added `.gitignore` coverage for `config/live/local/`.

## TDD Evidence

RED command:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q
```

RED output summary:

- `17 failed in 0.25s`
- Expected missing behavior was caught:
  - valid evidence with more than 10 observation days failed on old `exactly 10 trading days` rule
  - new missing path, non-trading date, ordering, counted window, duplicate seq reference, missing seq, wrong event type, wrong reconciliation semantics, wrong context, CRIT delivery semantics, template, and gitignore tests failed

GREEN command:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q
```

GREEN output summary:

- First green after implementation: `17 passed in 0.21s`
- Final focused gate after formatting cleanup: `17 passed in 0.15s`

## Commands Run And Results

- `pytest tests/test_m3b_signoff.py -q`: failed because `pytest` is not on PATH in this shell.
- `python -m pytest tests/test_m3b_signoff.py -q`: failed because `python` is not on PATH in this shell.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q`: baseline before changes, `4 passed in 0.11s`.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q`: RED after tests, `17 failed in 0.25s`.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q`: GREEN after implementation, `17 passed in 0.21s`.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check src/quant/live/signoff.py tests/test_m3b_signoff.py`: found two long lines and one import-sort issue; fixed.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check tests/test_m3b_signoff.py --fix`: fixed the import-sort issue.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check src/quant/live/signoff.py tests/test_m3b_signoff.py`: passed.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_m3b_signoff.py -q`: final focused gate, `17 passed in 0.15s`.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check .`: passed.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/lint-imports`: passed, `2 kept, 0 broken`.
- `git check-ignore -v config/live/local/`: passed, matched `.gitignore:14:config/live/local/`.
- `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest -q`: passed, `133 passed in 3.48s`.
- `git diff --check`: passed.

## Files Changed

- `.gitignore`
- `docs/runbooks/m3b_signoff_template.yaml`
- `src/quant/live/signoff.py`
- `tests/test_m3b_signoff.py`
- `.superpowers/sdd/task-1-report.md`

## Self-Review Findings

- Scope stayed within the requested files and did not add QMT adapter, live runner, Windows deployment, sample live config, real-order mode, or pilot-order features.
- Validator keeps the existing public API and resolves relative evidence paths from the signoff file directory first, then the current working directory.
- The tests cover the requested missing path, non-trading date, out-of-order date, invalid counted window, duplicate event seq reference, wrong event type, wrong reconciliation status/startup flag, wrong account/strategy/run id, wrong CRIT severity/delivery id, and valid evidence with extra observation days.
- I searched for an existing live config example section and did not find one, so I did not create a new live sample/config docs section. The secret-bearing local overlay path is ignored before any sample exists.

## Real M3b Evidence Artifact And QMT Gate

Search commands:

```bash
find . -type f \( -iname '*m3b*' -o -iname '*signoff*' -o -iname '*evidence*' \) -print
rg -n "gate: M3b|final_signoff|counted_window|M3b sign" -g '*.yaml' -g '*.yml' -g '*.md' .
find . -type f \( -name '*.yaml' -o -name '*.yml' \) -print
```

Result:

- No real M3b signoff evidence artifact exists in this checkout outside `docs/runbooks/m3b_signoff_template.yaml`.
- M4/QMT remains gated and blocked. I did not fabricate evidence.

## Concerns

- The real M3b promotion artifact is absent, so no QMT work should proceed.
- No existing live config example section was present to update with a placeholders-only note; only the required local overlay ignore rule was added.
