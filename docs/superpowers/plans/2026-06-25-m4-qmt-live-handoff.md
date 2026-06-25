# M4 QMT Live Handoff

> **For the next agentic worker:** use `superpowers:subagent-driven-development` to continue. Dispatch fresh workers per task, require task-scoped review after each task, and do not start M4a/QMT implementation until the M3b signoff gate below is satisfied.

**Date:** 2026-06-25

**Worktree:** `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m4-qmt-live`

**Branch:** `m4-qmt-live`

**Current HEAD:** `4faba59 Add mypy stub deps`

**Base commit:** `84b0db3 feat: add m3b signoff validation`

**Source M4 plan:** `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/codex_修改后架构/13_m4_qmt_live_开发计划.md`

## Executive Summary

M4-0 is implemented and reviewed. The local M4 starting-branch gates are now green, including the previously failing targeted mypy gate.

M4a, M4b, and M4c remain blocked by the M4 plan's hard precondition: there is no real operator-authored M3b signoff YAML outside the template. The repository currently contains only the M3b signoff template/docs/tests, not real signed evidence.

Do not implement QMT, `run_live.py`, Windows deployment, or pilot-order work until a real M3b signoff artifact exists and validates successfully.

## Current Git State

Committed M4-0 commits on `m4-qmt-live`:

- `d898554 feat: harden m3b evidence gate`
- `8b34c86 Remove local task report from tracking`
- `b96368d fix: align m3b signoff gate with paper journals`
- `93cdc82 fix: validate crit receipt timestamps`
- `85ab383 Untrack task 1 report artifact`
- `4faba59 Add mypy stub deps`

Committed branch diff vs `84b0db3` currently includes:

- `.gitignore`
- `README.md`
- `docs/runbooks/m3b_signoff_template.yaml`
- `pyproject.toml`
- `src/quant/live/engine.py`
- `src/quant/live/monitor.py`
- `src/quant/live/reconcile.py`
- `src/quant/live/signoff.py`
- `tests/golden_paper/events.jsonl`
- `tests/test_m3b_signoff.py`

Uncommitted/unreviewed working-tree changes present when this handoff was written:

- Modified: `README.md`
- Modified: `docs/runbooks/paper_daily_runbook.md`
- Modified: `tests/test_paper_runbook_docs.py`
- Untracked: `scripts/validate_m3b_signoff.py`
- Untracked: `tests/test_validate_m3b_signoff_cli.py`
- Untracked: this handoff file

Treat those uncommitted changes as in-progress local work, not accepted branch state. Review, test, and either commit or discard them before continuing.

## Completed Work

### M4-0: Evidence And Secrets Gate

Implemented and reviewed:

- M3b signoff template now includes `event_journal_path`, `trade_calendar_path`, `counted_window`, run context fields, disconnect drill fields, CRIT receipt fields, and final signoff fields.
- `validate_m3b_signoff(...)` loads the referenced trade calendar and JSONL event journal.
- Validator rejects non-trading dates and non-increasing trading-day dates.
- Validator requires a declared counted window with at least 10 counted trading days while allowing extra observation days.
- Validator verifies referenced startup reconciliation, close reconciliation, disconnect, recovery, and CRIT receipt event seq values against the archived event journal.
- Validator checks event semantics: event type, event date, status, startup flag, account id, strategy id, run id, CRIT severity, delivery id, disconnect safe state, and recovery state/reason.
- Validator rejects malformed CRIT receipt timestamps instead of skipping event validation.
- Validator validates `final_signoff.signed_at` as an ISO timestamp.
- Paper event producers were aligned with the validator:
  - `Reconciler` emits run/strategy/account context in reconciliation events.
  - `PaperEngine` passes real context into `Reconciler`.
  - `RuntimeMonitor` emits run/strategy/account context in gateway disconnect and recovery events.
- `config/live/local/` is ignored for real live local overlays.
- README states committed live config examples may contain placeholders only, and real overlays belong in `config/live/local/`.
- Dev optional dependencies now include `pandas-stubs` and `types-PyYAML`, allowing the M4 targeted mypy gate to pass.
- Tests include synthetic negative cases and a real-producer signoff path using `EventJournal`, `Reconciler`, `RuntimeMonitor`, and `AlertManager`.

### Reviews Completed

Subagent reviews approved:

- Initial M4-0 task review after report artifact was untracked.
- Branch-level review after producer/schema alignment fixes.
- Final CRIT receipt timestamp fix review.
- Dev stub dependency fix review.
- Latest full-branch review: `M4-0 branch quality: Approved`; `Can M4a/QMT work start now: No`.

## Latest Verified Gates

Run from `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.worktrees/m4-qmt-live`.

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/mypy src/quant/live/gateway src/quant/live/oms.py src/quant/risk
```

Observed: `Success: no issues found in 8 source files`

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest -q
```

Observed: `142 passed`

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check .
```

Observed: `All checks passed!`

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/lint-imports
```

Observed: `core does not depend outward KEPT`, `risk does not depend on live runtime KEPT`

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --risk config/risk/global.yaml --max-bars 20
```

Observed: `final state: NORMAL`

Disconnect-drill Paper replay was run with a temporary paper config and:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper "$paper" --risk config/risk/global.yaml --max-bars 1 --disconnect-drill --disconnect-reason "network drill"
```

Observed: `final state: NORMAL`; drill result had `reconciliation_status: OK` and `final_state: NORMAL`.

## Blocking Condition

M4a/QMT is blocked because no real M3b signoff evidence artifact exists.

The M4 plan requires all of the following before QMT work:

- A real M3b signoff YAML outside the template.
- `final_signoff.approved: true`.
- Non-empty operator and signed timestamp.
- `event_journal_path` pointing to the archived Paper JSONL journal.
- `trade_calendar_path` pointing to the project trade calendar used for counted days.
- Declared `counted_window` with at least 10 counted trading days.
- Strictly increasing counted trading dates from the trade calendar.
- Daily startup and close reconciliation event seq evidence.
- One disconnect drill seq and recovery seq.
- One CRIT delivery receipt event seq.
- No unresolved manual intervention.
- Successful validation through the hardened M3b signoff validator.

Current evidence search found only template/docs/tests:

- `docs/runbooks/m3b_signoff_template.yaml`
- `src/quant/live/signoff.py`
- `tests/test_m3b_signoff.py`

No operator-authored `m3b_signoff.yaml` candidate was found.

## Gate Unlock Procedure

When the real M3b observation window is complete:

1. Create an operator-authored `m3b_signoff.yaml` outside the template.
2. Place the archived `events.jsonl` and trade calendar beside it or use absolute paths.
3. Validate it with the hardened validator.

If the CLI intake script is accepted and committed, use:

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

Expected success text: `M4a may start`.

If the CLI intake script is not accepted, validate directly with Python:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/python - <<'PY'
from pathlib import Path
from quant.live.signoff import validate_m3b_signoff

validate_m3b_signoff(Path("path/to/m3b_signoff.yaml"))
print("M3b signoff validated. M4a may start.")
PY
```

4. Run the local gate again:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest -q
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check .
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/lint-imports
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/mypy src/quant/live/gateway src/quant/live/oms.py src/quant/risk
```

5. Run normal Paper replay and disconnect-drill Paper replay.
6. Commit and tag the completed M3 state only after the real evidence validates.
7. Only then dispatch M4a workers.

## Uncommitted CLI Intake Work

There is local uncommitted work that appears to add a signoff validation CLI:

- `scripts/validate_m3b_signoff.py`
- `tests/test_validate_m3b_signoff_cli.py`
- README and runbook documentation updates for `M4a may start`

Recommended next action before any QMT work:

1. Review this local CLI work.
2. Run:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest tests/test_validate_m3b_signoff_cli.py tests/test_paper_runbook_docs.py -q
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check scripts/validate_m3b_signoff.py tests/test_validate_m3b_signoff_cli.py tests/test_paper_runbook_docs.py README.md docs/runbooks/paper_daily_runbook.md
```

3. If it passes review, commit it as a small M4-0 follow-up.
4. If it is not wanted, remove the local changes deliberately.

Do not let this local CLI work be confused with the real M3b evidence. A CLI can validate evidence; it is not itself evidence.

## Remaining Work After Gate Unlocks

### M4a: QMT Adapter Dry Run

Start only after the real M3b signoff validates.

Recommended subagent task order:

1. Live config schema and placeholder sample.
   - Add `config/live/qmt_dual_ma_510300.example.yaml` with placeholders only.
   - Add `LiveStrategyConfig` and `load_live_strategy_config()` for `runtime_mode: live`.
   - Keep ordinary `load_strategy_config()` restricted to `backtest | paper`.
   - Tests: live config accepts live only through live loader; normal loader rejects live.

2. Gateway lifecycle compatibility.
   - Extend `GatewayBase` with `connect(conf)`, `close()`, and `subscribe(symbols)`.
   - Add compatible `SimGateway` implementations.
   - Tests must prove Paper replay behavior is unchanged.

3. Durable external-order identity model.
   - Add storage for `local_order_id`, `client_order_ref`, `broker_order_id`, and `request_id`.
   - Enforce uniqueness.
   - Tests must cover lookup by each external id and repeated reports.

4. `QmtGateway` dry-run adapter.
   - Create `src/quant/live/gateway/qmt.py`.
   - Keep all `xtquant` imports inside this file.
   - Use existing DTOs from `quant.core.contract` / `quant.live.types`.
   - Implement mapping for account, positions, order snapshots, trade snapshots, submit, cancel, query, and callbacks using fake xtquant payloads in tests.
   - Add callback-before-return pending buffer and deterministic replay.
   - Add reconnect query replay mapping.
   - Fail safe if a callback cannot be mapped to a local order.
   - Real orders must be blocked when `allow_real_orders: false`.

5. Live gateway factory.
   - Extend `src/quant/live/gateway/factory.py`.
   - Preserve SimGateway for Paper.
   - QMT factory must fail closed if `xtquant` is unavailable.
   - `allow_real_orders: false` still allows query-only/dry-run construction.

6. `scripts/run_live.py`.
   - Default mode is query-only/dry-run.
   - Query-only dry-run must not load strategy code, instantiate order-capable execution, or call `OrderManager.submit_order()`.
   - Real order mode requires both CLI flag and config opt-in.
   - Startup reconciliation must pass before any strategy order is accepted.

7. Live snapshot initialization.
   - Explicit query-only initialization command.
   - Only allowed on empty store with no orders/trades.
   - Requires operator, reason, account-id confirmation, and precheck evidence.
   - Writes JSONL event.
   - Normal live startup reconciliation still fails on empty store before initialization.

M4a local exit gate:

```bash
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/pytest -q
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/ruff check .
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/lint-imports
/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant/.venv/bin/mypy src/quant/live/gateway src/quant/live/oms.py src/quant/risk
```

Then run dry-run verification on the Windows QMT host.

### M4b: Windows Deployment And Recovery

Start after M4a local dry-run is ready.

Required deliverables:

- `docs/runbooks/qmt_live_runbook.md`.
- Windows service/NSSM example under `deploy/windows/`.
- Pre-open self-check command.
- Backup and restore drill docs.
- M4 pilot evidence validator or M3b validator extension.
- Windows QMT dry-run evidence.
- Restart drill evidence.
- Backup restore evidence.

### M4c: Small-Capital Pilot Gate

Start only after M4a/M4b evidence exists.

Required deliverables:

- Pilot config with `allow_real_orders: true`, strict risk limits, and pilot capital in gitignored local config or machine secrets only.
- Real order mode must require config and CLI opt-in.
- Live reconciliation default must set `auto_repair_cash_drift_below: 0`.
- Pilot observation window: at least 10 counted trading days across at least 2 calendar weeks.
- Daily startup and close reconciliation with zero unresolved difference.
- At least one active restart drill.
- At least one CRIT alert drill visible on the phone-side channel.
- M4 pilot signoff.

## Guardrails For Future AI

- Do not start QMT work without validated real M3b evidence.
- Do not fabricate signoff evidence.
- Do not commit broker account ids, QMT paths, credentials, pilot capital, or local live overlays.
- Keep `xtquant` imports only in `src/quant/live/gateway/qmt.py`.
- Strategies must continue importing only `quant.core.contract`.
- Default live behavior must be query-only/dry-run.
- `allow_real_orders: false` must block every real submission path.
- Unknown broker state, reconciliation failure, gateway query failure, or unmapped callback must freeze or halt; never continue silently.
- Every implementation task should use TDD, commit separately, and receive task-scoped review before the next task starts.

## Suggested Next Controller Decision

If no real M3b signoff exists, do not dispatch M4a workers. Instead:

1. Decide whether to keep and commit the uncommitted CLI intake work.
2. Continue M3b Paper observation until the real signoff package exists.
3. Validate the signoff.
4. Tag the completed M3 state.
5. Resume this branch and start M4a using the task order above.

