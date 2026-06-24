# M3 Paper Pre-Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the referenced M3 plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare safe execution of the completed M3 Paper plan without changing strategy boundaries, losing determinism, or accidentally mixing unrelated documentation edits into implementation commits.

**Architecture:** The source implementation plan is `codex_修改后架构/12_m3_paper_开发计划.md`. Execution should keep the two-phase boundary intact: M3a builds deterministic local Paper replay, and M3b uses the same runtime for the 10-trading-day observation gate. This document is a pre-development wrapper: it records current repository state, execution order, extra interface decisions, and quality gates before coding starts.

**Tech Stack:** Python 3.11+, pytest, pydantic v2, PyYAML, pandas, stdlib `sqlite3`, stdlib `queue`, stdlib `threading`, loguru, existing `Matcher`, `CostModel`, `Portfolio`, ruff, import-linter, uv or the checked-in `.venv`.

## Global Constraints

- Market scope: A股 ETF only for M3; daily bars only.
- Runtime scope: Paper trading only; no QMT, no true broker gateway, no real-money order submission.
- Phase boundary: M3a completion means local deterministic Paper replay passes; M3 is not accepted as the real-money pre-gate until M3b completes 10 trading days of Paper observation with daily reconciliation, one disconnect drill, and verified CRIT alert delivery.
- Strategy boundary: strategies may import `quant.core.contract` plus standard library, numpy, and pandas only.
- Runtime mode: `runtime_mode` may be `backtest` or `paper`; `live` is still rejected until M4.
- Order path: every Paper order must pass `RiskEngine` before `OrderManager` sends it to `SimGateway`.
- Daily-bar execution: `set_target()` called from a 15:00 daily bar records a target intent; the Paper runtime converts it into broker orders at the next tradable bar open, and trading-session checks run at that broker-send time.
- Persistence: every local order is written to SQLite before any gateway send attempt.
- Audit trail: every order, trade, rejection, reconciliation, alert, and manual ops action is appended to JSONL.
- Recovery: Paper engine startup must reconcile local state and gateway state before accepting strategy orders.
- Failure semantics: risk exceptions, gateway disconnects, stale market data, and reconciliation failures freeze or halt safely; they never silently allow new opening orders.
- Verification requirement: every implementation task ends with a fresh test command and an explicit commit.
- Deliberately excluded: QMT, true live mode, real broker order submission, minute/tick bars, web UI, multi-account production operations, and mobile-command trading.

---

## Current Repository Baseline

- Source plan read: `codex_修改后架构/12_m3_paper_开发计划.md`.
- Current repo root for development: `/Users/shenxi/Desktop/WORK-SPACE/个人量化系统/quant`.
- Existing quality gate is green using the project virtualenv:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/lint-imports
```

Observed output:

```text
24 passed
All checks passed!
Contracts: 1 kept, 0 broken.
```

- Plain `pytest`, `ruff`, and `lint-imports` are not on shell `PATH`; use `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/lint-imports`, and `.venv/bin/python` unless the environment is activated.
- Current worktree is not clean before M3 coding:

```text
 M codex_修改后架构/01_architecture.md
 M codex_修改后架构/README.md
?? codex_修改后架构/12_m3_paper_开发计划.md
?? docs/superpowers/plans/2026-06-24-m3-paper-pre-dev.md
```

Implementation commits must not accidentally stage the existing architecture doc edits unless the owner explicitly wants them included.

## Pre-Development Decisions

1. Treat `codex_修改后架构/12_m3_paper_开发计划.md` as the canonical M3 task list.
2. Execute M3a Tasks 1-10 before any M3b observation work.
3. Execute M3b Task 11 as documentation and test scaffolding only after M3a full gate is green.
4. Do not begin M4 planning or QMT work until both M3a and M3b definitions of done are checked.
5. Add `runtime/` to `.gitignore` before the first command that writes `runtime/paper/*`.
6. Do not let `quant.live` leak into `quant.core`; the existing import-linter contract must remain green.
7. Do not let strategies import `quant.live`, `quant.data`, `quant.risk`, `quant.backtest`, or broker-specific modules.
8. Use explicit `git add` file lists from each M3 task; avoid broad `git add .` while architecture docs are dirty.

## Interface Adjustments To Lock Before Coding

The M3 plan largely matches the current codebase, with these execution-time clarifications:

- `StrategyConfig.runtime_mode` currently accepts only `"backtest"`; Task 1 expands it to `"backtest" | "paper"` and still rejects `"live"`.
- `RiskConfig` currently has only `max_order_value` and `max_position_value`; Task 1 expands it with `max_gross_exposure_pct` and `max_orders_per_minute`.
- `Context` already contains the API surface that `PaperContext` needs, so M3 should not modify `quant.core.contract.context` unless tests reveal a true mismatch.
- `DataService` has no public bar replay iterator. During Task 8, add a small public method such as `iter_bars(universe: list[str]) -> list[Bar]` or `load_bars(universe: list[str]) -> list[Bar]`, and use it from both future Paper code and any later backtest cleanup. Do not access `DataService._bars` from new `quant.live` code.
- `SimGateway` should instantiate `CostModel` using the same ETF cost values as the current backtest default: commission rate `0.00025`, commission min `5`, stamp tax `0`, transfer fee `0`.
- `OmsStore.save_kv()` and `load_kv()` should JSON-encode values with stable ordering where possible; counters such as `next_order_seq` must round-trip as numbers, not stringly typed state.
- Event timestamps in replay must come from the simulated market clock. Wall-clock timestamps will break golden JSONL determinism.
- CRIT alert delivery in M3a is an audited event contract. Actual phone-side delivery acceptance belongs to M3b and must be proven during the observation window.

## Execution Waves

### Wave 0: Start Clean And Protect Runtime State

**Files:**
- Modify: `.gitignore`

**Purpose:** Prepare a safe implementation surface before touching M3 code.

- [ ] **Step 1: Confirm baseline**

Run:

```bash
git status --short
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/lint-imports
```

Expected: existing tests, ruff, and import-linter pass. Dirty documentation files may exist, but no implementation files should be modified yet.

- [ ] **Step 2: Ignore runtime state**

Add this line to `.gitignore`:

```gitignore
runtime/
```

- [ ] **Step 3: Verify ignore rule**

Run:

```bash
mkdir -p runtime/paper
touch runtime/paper/meta.db runtime/paper/events.jsonl
git status --short --ignored runtime
rm -rf runtime
```

Expected: `runtime/` is ignored and removed after the check.

- [ ] **Step 4: Commit preflight change**

Run:

```bash
git add .gitignore
git commit -m "chore: ignore paper runtime state"
```

Expected: commit contains only `.gitignore`.

### Wave 1: M3a Foundation

**Source tasks:** M3 Task 1 through Task 4.

**Files introduced or changed:**
- `src/quant/core/config.py`
- `src/quant/live/__init__.py`
- `src/quant/live/config.py`
- `src/quant/live/types.py`
- `src/quant/live/events.py`
- `src/quant/live/gateway/base.py`
- `src/quant/live/store.py`
- `src/quant/risk/checks.py`
- `src/quant/risk/pipeline.py`
- `config/paper.yaml`
- `config/risk/global.yaml`
- `config/strategies/dual_ma_510300_paper.yaml`
- `tests/test_live_config.py`
- `tests/test_live_events.py`
- `tests/test_live_store.py`
- `tests/test_risk_pipeline.py`

**Exit gate:**

```bash
.venv/bin/pytest tests/test_live_config.py tests/test_live_events.py tests/test_live_store.py tests/test_risk_pipeline.py -q
.venv/bin/pytest tests/test_config.py tests/test_contract.py tests/test_portfolio_costs.py -q
.venv/bin/ruff check src/quant/core/config.py src/quant/live src/quant/risk tests/test_live_config.py tests/test_live_events.py tests/test_live_store.py tests/test_risk_pipeline.py
.venv/bin/lint-imports
```

Expected: Paper config, DTOs, event journal, SQLite store, and risk pipeline pass without breaking existing core contracts.

### Wave 2: M3a Order Path

**Source tasks:** M3 Task 5 through Task 7.

**Files introduced:**
- `src/quant/live/oms.py`
- `src/quant/live/gateway/sim.py`
- `src/quant/live/reconcile.py`
- `tests/test_oms.py`
- `tests/test_sim_gateway.py`
- `tests/test_reconcile.py`

**Exit gate:**

```bash
.venv/bin/pytest tests/test_oms.py tests/test_sim_gateway.py tests/test_reconcile.py -q
.venv/bin/pytest tests/test_live_store.py tests/test_risk_pipeline.py tests/test_matcher.py tests/test_portfolio_costs.py -q
.venv/bin/ruff check src/quant/live/oms.py src/quant/live/gateway src/quant/live/reconcile.py tests/test_oms.py tests/test_sim_gateway.py tests/test_reconcile.py
.venv/bin/lint-imports
```

Expected: order persistence-before-send, risk rejection, idempotent broker trades, simulated fills, disconnect injection, and reconciliation failure semantics are all covered.

### Wave 3: M3a Engine, Ops, And Regression Gate

**Source tasks:** M3 Task 8 through Task 10.

**Files introduced or changed:**
- `src/quant/data/service.py`
- `src/quant/live/context.py`
- `src/quant/live/engine.py`
- `src/quant/live/execution.py`
- `src/quant/live/alerts.py`
- `src/quant/live/monitor.py`
- `scripts/run_paper.py`
- `scripts/ops.py`
- `tests/test_paper_engine.py`
- `tests/test_alerts_monitor.py`
- `tests/test_ops_cli.py`
- `tests/test_paper_golden.py`
- `tests/golden_paper/events.jsonl`
- `tests/golden_paper/orders.csv`
- `tests/golden_paper/trades.csv`
- `docs/runbooks/paper_daily_runbook.md`
- `README.md`

**DataService addition:**

Add a public replay method before implementing `PaperEngine`:

```python
from quant.core.contract import Bar, Instrument


def load_bars(self, universe: list[str]) -> list[Bar]:
    rows = self._bars[self._bars["symbol"].isin(universe)].sort_values(["dt", "symbol"])
    reject_missing_rows(rows)
    return [
        Bar(
            symbol=row.symbol,
            freq="1d",
            dt=row.dt.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            amount=float(row.amount),
            pre_close=float(row.pre_close),
            limit_up=float(row.limit_up),
            limit_down=float(row.limit_down),
            suspended=bool(row.suspended),
        )
        for row in rows.itertuples()
        if row.data_status == "ok"
    ]
```

The method should preserve the current backtest ordering semantics: sort by `dt, symbol`, reject missing rows, keep only `data_status == "ok"`, and construct timezone-aware `Bar` objects.

**Exit gate:**

```bash
.venv/bin/pytest tests/test_paper_engine.py tests/test_alerts_monitor.py tests/test_ops_cli.py tests/test_paper_golden.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/lint-imports
.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
.venv/bin/python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status
```

Expected: full test suite remains green; replay creates deterministic Paper artifacts; ops status prints one of `NORMAL`, `FREEZE_OPEN`, or `HALT`.

### Wave 4: M3b Observation Gate

**Source task:** M3 Task 11.

**Files introduced or changed:**
- `docs/runbooks/paper_observation_checklist.md`
- `tests/test_m3_paper_gate_docs.py`
- `README.md`

**Exit gate before real observation starts:**

```bash
.venv/bin/pytest tests/test_m3_paper_gate_docs.py -q
.venv/bin/ruff check tests/test_m3_paper_gate_docs.py
```

Expected: the M3b checklist explicitly blocks M4 until 10 trading days, daily reconciliation zero difference, a disconnect drill, CRIT alert delivery, and no unresolved manual intervention are complete.

**Operational observation gate:**

- [ ] Run the same Paper strategy config for at least 10 trading days.
- [ ] Record date, strategy id, account id, final engine state, order count, trade count, reject count, reconciliation status, alerts, and operator notes each day.
- [ ] Archive `runtime/paper/meta.db`, `runtime/paper/events.jsonl`, and the strategy config snapshot each day.
- [ ] Complete one disconnect drill.
- [ ] Complete one CRIT alert delivery drill to the chosen phone-side channel.
- [ ] Sign off M3b only after every counted day has zero unresolved reconciliation difference.

## Risk Register

| Risk | Impact | Pre-development control |
|---|---|---|
| Dirty docs are accidentally included in M3 commits | History becomes hard to review | Use explicit `git add` lists; review `git diff --cached --stat` before every commit |
| `runtime/paper/*` is committed | Local state pollutes source control | Add `runtime/` to `.gitignore` in Wave 0 |
| New live code reaches into `DataService._bars` | Private coupling spreads | Add a public `load_bars()` method during Wave 3 |
| Replay event timestamps use wall-clock time | Golden JSONL flakes | Inject deterministic clock tied to simulated bar time |
| Risk session check rejects daily `set_target()` orders | Paper strategy appears broken after 15:00 bars | Flush target intents at next bar synthetic `09:31 Asia/Shanghai` send time |
| Gateway reconnect auto-resumes trading | Unsafe recovery | Reconnect only restores connectivity; engine resumes only after reconciliation passes |
| SQLite writes happen after gateway send | Lost local order fact during crash | `OrderManager.submit_order()` must save `SUBMITTING` before `send_order()` |
| Duplicate broker trade callback double-applies portfolio | Cash and positions drift | `OmsStore.save_trade_once()` is the idempotency boundary |
| CRIT event lacks operator context | M3b alert drill cannot be audited | Require `run_id`, `strategy_id`, `account_id`, `last_event_seq`, `local_time`, and `market_time` |
| Import boundaries weaken strategy contract | Strategies gain hidden platform dependencies | Keep `tests/test_import_boundaries.py` and `lint-imports` in every full gate |

## Commit Rhythm

Use one commit per source task, plus the Wave 0 preflight commit. Keep the commit messages from the source M3 plan unless a task is intentionally split:

```text
chore: ignore paper runtime state
feat: add paper runtime config
feat: add live gateway contracts and event journal
feat: add sqlite oms store
feat: add paper risk pipeline
feat: add paper order manager
feat: add simulated paper gateway
feat: add paper reconciliation
feat: add paper replay engine
feat: add paper alerts and ops controls
test: add paper golden regression gate
docs: add m3b paper observation gate
```

## Development Start Checklist

- [ ] Confirm whether current architecture doc edits should be committed separately before M3 implementation.
- [ ] Confirm implementation will run from the `quant/` repo root, not the outer workspace directory.
- [ ] Use `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/lint-imports`, and `.venv/bin/python` command paths or activate the project virtualenv.
- [ ] Add `runtime/` to `.gitignore`.
- [ ] Execute M3 source tasks in order; do not jump to engine work before store, risk, OMS, gateway, and reconciliation are green.
- [ ] Run the full gate after Wave 3 before writing M3b observation docs.
- [ ] Keep M4 out of scope until M3b has real observation evidence.

## Self-Review

- Spec coverage: This wrapper covers the completed M3 plan, current baseline, worktree hygiene, interface mismatches, execution order, quality gates, and M3a/M3b acceptance boundaries.
- Placeholder scan: No placeholders are left for implementation decisions that must be made before coding.
- Type consistency: Names match the source plan: `PaperConfig`, `OrderRequest`, `GatewayBase`, `OmsStore`, `RiskEngine`, `OrderManager`, `SimGateway`, `Reconciler`, `ExecutionRouter`, `PaperContext`, and `PaperEngine`.
