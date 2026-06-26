# M3 Paper Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair M3 Paper so it can support the M3b 10-trading-day observation gate with restart recovery, reconciliation evidence, kill switch enforcement, disconnect drills, and auditable alert delivery.

**Architecture:** Keep the existing modular monolith and Paper-only M3 boundary. `PaperEngine` remains the strategy lifecycle/replay coordinator, while runtime assembly, gateway contracts, OMS state transitions, reconciliation, monitoring, and ops recovery are hardened to match the architecture documents. `FREEZE_OPEN` is a recoverable safe state after system reconciliation passes; `HALT` always requires manual confirmation.

**Tech Stack:** Python 3.11+, Pydantic v2, SQLite, JSONL event journal, pytest, ruff, import-linter, mypy.

## Global Constraints

- Runtime scope: Paper trading only; no QMT, no true broker gateway, no real-money order submission.
- M3b acceptance requires 10 trading days, daily startup and close reconciliation zero unresolved difference, one disconnect drill, verified CRIT alert delivery evidence, and no unresolved manual intervention.
- `FREEZE_OPEN` can auto-recover only for system faults after OK/REPAIRED reconciliation; manual freeze remains manual.
- `HALT` must never auto-recover; it requires explicit operator resume with reason, prechecks, and reconciliation evidence.
- Strategies must continue to import only `quant.core.contract`.
- Every Paper order must pass RiskEngine before OrderManager sends it to a gateway.
- Every persisted state change must be auditable through SQLite and/or JSONL events.
- `max_cancel_ratio_daily` is parsed in M3 but not enforced; this limitation must be explicit.

---

### Task 1: Gateway Contract And Type Hardening

**Files:**
- Modify: `src/quant/live/gateway/base.py`
- Modify: `pyproject.toml`
- Test: `tests/test_live_events.py`

**Interfaces:**
- Produces: `GatewayBase.set_callbacks(on_order: Callable[[BrokerOrderSnapshot], None], on_trade: Callable[[BrokerTradeSnapshot], None])`
- Produces dev command: `.venv/bin/mypy src/quant/live/gateway src/quant/live/oms src/quant/risk`

- [ ] Write failing tests that inspect `GatewayBase.__annotations__` or use `typing.get_type_hints()` to confirm callback types are broker snapshots.
- [ ] Run `pytest tests/test_live_events.py -q` and confirm failure.
- [ ] Update callback type annotations and add `mypy` to dev dependencies/config.
- [ ] Run `pytest tests/test_live_events.py -q`, `ruff check src/quant/live/gateway tests/test_live_events.py`, and mypy targeted check.

### Task 2: SimGateway Recovery And Atomic Fill Semantics

**Files:**
- Modify: `src/quant/core/portfolio.py`
- Modify: `src/quant/live/gateway/sim.py`
- Test: `tests/test_sim_gateway.py`

**Interfaces:**
- Produces: `Portfolio.from_snapshot(account: Account, positions: dict[str, Position]) -> Portfolio`
- Produces: `SimGateway.from_snapshot(account: Account, positions: dict[str, Position], active_orders: list[Order], trades: list[Trade], account_id: str, initial_cash: float, volume_limit_pct: float = 0.05) -> SimGateway`
- Produces: `SimGateway.mark_new_day() -> None`

- [ ] Add tests for restart recovery, active-order continuation, no duplicate fill after callback failure, and T+1 sellable release.
- [ ] Run `pytest tests/test_sim_gateway.py -q` and confirm failures.
- [ ] Implement portfolio and gateway recovery, callback-safe fill ordering, broker sequence restoration, and mark-new-day.
- [ ] Run `pytest tests/test_sim_gateway.py tests/test_portfolio_costs.py -q` and ruff on touched files.

### Task 3: OMS State Machine, Event Idempotency, And Atomic Order IDs

**Files:**
- Modify: `src/quant/live/store.py`
- Modify: `src/quant/live/oms.py`
- Test: `tests/test_live_store.py`
- Test: `tests/test_oms.py`

**Interfaces:**
- Produces: `OmsStore.next_order_id(prefix: str = "O") -> str`
- Produces broker order state validation in `OrderManager.on_broker_order()`

- [ ] Add tests for terminal status rollback rejection, filled quantity decrease rejection, stale snapshot auditing, duplicate submitted event avoidance, and unique order id allocation.
- [ ] Run `pytest tests/test_oms.py tests/test_live_store.py -q` and confirm failures.
- [ ] Implement atomic order IDs and broker snapshot validation/idempotency.
- [ ] Run `pytest tests/test_oms.py tests/test_live_store.py -q` and ruff on touched files.

### Task 4: Global Risk Config And Kill Switch Wiring

**Files:**
- Modify: `src/quant/live/config.py`
- Modify: `src/quant/live/engine.py`
- Modify: `scripts/run_paper.py`
- Test: `tests/test_live_config.py`
- Test: `tests/test_paper_engine.py`

**Interfaces:**
- Produces: `PaperEngine(..., global_risk_config: GlobalRiskConfig | None = None, gateway_factory: Callable[..., GatewayBase] | None = None)`
- CLI: `scripts/run_paper.py --risk config/risk/global.yaml`

- [ ] Add tests that global risk changes price collar/order limit behavior and that equity loss triggers FREEZE_OPEN/HALT events.
- [ ] Run targeted tests and confirm failures.
- [ ] Merge global and strategy risk so strategy can only tighten configured limits.
- [ ] Call `RiskEngine.on_equity()` after account valuation updates and persist resulting state changes.
- [ ] Run `pytest tests/test_live_config.py tests/test_paper_engine.py tests/test_risk_pipeline.py -q`.

### Task 5: Full Reconciliation And Close Reconciliation

**Files:**
- Modify: `src/quant/live/reconcile.py`
- Modify: `src/quant/live/engine.py`
- Test: `tests/test_reconcile.py`
- Test: `tests/test_paper_engine.py`

**Interfaces:**
- Produces: `ReconciliationResult.account_diffs: dict[str, float]`
- Produces: `ReconciliationResult.position_value_diffs: dict[str, float]`
- Produces close reconciliation in `PaperEngine.run_replay()`

- [ ] Add tests for frozen/market_value/total_value drift, position sellable/market value drift, and close reconciliation event.
- [ ] Run targeted tests and confirm failures.
- [ ] Implement extended diffs and close reconciliation; close failure sets HALT.
- [ ] Run `pytest tests/test_reconcile.py tests/test_paper_engine.py -q`.

### Task 6: Recovery Semantics, Disconnect Drill, Alert Receipts, And Ops Resume

**Files:**
- Modify: `src/quant/live/alerts.py`
- Modify: `src/quant/live/monitor.py`
- Modify: `src/quant/live/engine.py`
- Modify: `scripts/run_paper.py`
- Modify: `scripts/ops.py`
- Test: `tests/test_alerts_monitor.py`
- Test: `tests/test_paper_engine.py`
- Test: `tests/test_ops_cli.py`

**Interfaces:**
- Produces: `AlertManager(..., clock: Callable[[], datetime] | None = None, delivery_dir: Path | None = None)`
- Produces: `PaperEngine.run_disconnect_drill(reason: str) -> dict[str, object]`
- CLI: `run_paper.py --disconnect-drill --disconnect-reason "..."`
- CLI: `ops.py resume --reconciliation-seq N [--allow-halt-resume]`

- [ ] Add tests for FREEZE_OPEN auto-recovery after OK reconciliation, HALT no auto-recovery, alert dedupe by context/reason, delivery receipt creation, disconnect drill, and ops resume evidence validation.
- [ ] Run targeted tests and confirm failures.
- [ ] Implement recovery state tracking, alert receipt writing, disconnect drill, and stricter ops resume.
- [ ] Run `pytest tests/test_alerts_monitor.py tests/test_paper_engine.py tests/test_ops_cli.py -q`.

### Task 7: M3b Signoff Evidence And Final Gates

**Files:**
- Create: `docs/runbooks/m3b_signoff_template.yaml`
- Create: `src/quant/live/signoff.py`
- Modify: `tests/test_m3_paper_gate_docs.py`
- Modify: `tests/test_paper_golden.py`

**Interfaces:**
- Produces: `validate_m3b_signoff(path: Path) -> None`

- [ ] Add tests that invalid signoff evidence fails and complete 10-day evidence passes.
- [ ] Add semantic invariant tests for Paper events.
- [ ] Implement signoff validator and template.
- [ ] Run full gate: `pytest -q`, `ruff check .`, `lint-imports`, targeted mypy, normal replay, and disconnect-drill replay.
