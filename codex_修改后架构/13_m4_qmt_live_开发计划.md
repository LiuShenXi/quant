# M4 QMT Live Trading Draft Plan

**Draft status:** This plan is blocked until a real M3b signoff artifact exists. The M3 implementation and local gates are green, but the repository currently contains only the M3b signoff template; M4 execution must not start until M3b has a validated signoff with `final_signoff.approved: true`.

**Goal:** Define the path from a validated M3b Paper gate to a tightly capped QMT real-money pilot, without changing the strategy contract or bypassing the M3 safety path.

**Architecture:** M4 keeps the same strategy-facing contract and OMS/risk/reconciliation pipeline built in M3. The main new surface is a QMT-backed `GatewayBase` adapter plus live runtime configuration, Windows deployment/runbook, broker-side reconciliation evidence, and a small-capital observation gate. M4 must not introduce research features, web UI, minute/tick strategy logic, multi-account production operations, or mobile-command trading.

## Hard Preconditions Before QMT Work

- A real M3b signoff YAML exists outside the template and passes a hardened evidence validator.
- The M3b signoff has `final_signoff.approved: true`, operator, and signed timestamp.
- The signed M3b evidence contains at least 10 counted trading days, and the signoff explicitly declares the counted window used for promotion.
- Counted trading days must be strictly increasing trading dates from the project trade calendar, with daily startup and close reconciliation event sequence evidence, one disconnect drill, one CRIT delivery receipt, and no unresolved manual intervention.
- The M3b evidence validator checks event sequence references against the archived JSONL event journal and rejects missing, duplicated, or out-of-order trading days.
- Real live config overlays such as `config/live/local/` are ignored before any sample live config is added.
- The completed M3 code state is committed and tagged before M4 work starts.
- Fresh local gate passes on the M4 starting branch: `pytest -q`, `ruff check .`, `lint-imports`, targeted `mypy`, normal Paper replay, and disconnect-drill Paper replay.
- Real broker account id, QMT session paths, credentials, and pilot capital values are stored only in gitignored local config or machine secrets, never in committed config.

## Scope Boundary

- Runtime scope: A股 ETF only, one account, one strategy instance, daily-bar strategy cadence.
- Broker scope: QMT / miniQMT through xtquant, isolated under `src/quant/live/gateway/`.
- Capital scope: small pilot capital only; the pilot amount must be written into the gitignored local live config before first run.
- Strategy scope: existing `DualMA` strategy must run without strategy-code changes.
- Safety scope: startup reconciliation must pass before any order can be accepted.
- Failure scope: unknown broker state, reconciliation failure, gateway query failure, or missing callback evidence must freeze or halt, never continue silently.
- Deliberately excluded: new strategy research, QMT-specific strategy imports, direct broker access from strategies, web UI, multi-account routing, automatic capital scaling, and phone-message trading commands.

## M4-0: Evidence And Secrets Gate

**Purpose:** Make the M3b-to-M4 gate executable before any QMT code is written.

**Tasks:**

1. Harden M3b signoff evidence.
   - Extend `docs/runbooks/m3b_signoff_template.yaml` with `event_journal_path` and `trade_calendar_path`.
   - Extend `validate_m3b_signoff(...)` to load the referenced trade calendar and event journal.
   - Reject dates that are not in the project trade calendar.
   - Reject non-increasing trading day dates.
   - Require a declared counted window with at least 10 counted trading days; extra observation days may remain in the evidence and must not be discarded.
   - Verify each startup reconciliation seq, close reconciliation seq, disconnect drill seq, recovery seq, and CRIT receipt event seq exists in the archived JSONL event journal.
   - Validate event semantics, not just existence: expected event `type`, `payload.status`, `payload.startup`, event date, account id, strategy id, run id, CRIT severity, and delivery id must match the signoff row that references it.
   - Add tests for missing journal paths, non-trading dates, out-of-order dates, invalid counted windows, duplicated event seq references, wrong event type, wrong reconciliation status/startup flag, wrong account/strategy/run id, wrong CRIT severity/delivery id, and valid complete evidence with more than 10 observation days.

2. Add live local config isolation before any live sample config.
   - Add `.gitignore` coverage for real live config overlays such as `config/live/local/`.
   - Add a short note in the live config example section that committed files may contain placeholders only.

3. Validate the real M3b signoff artifact.
   - Run the hardened validator against the actual M3b evidence file.
   - Commit and tag the completed M3 state only after the validator passes.

**Exit criteria:**

- Hardened M3b signoff tests pass.
- Real M3b evidence validates against trade calendar and archived event journal.
- Real live account ids, QMT paths, credentials, and pilot capital values cannot be committed through the planned live config path.

## M4a: QMT Adapter Dry Run

**Purpose:** Add the QMT adapter and live runtime shape while keeping real-money order submission disabled by default.

**Tasks:**

1. Add live configuration models and sample config.
   - Create `config/live/qmt_dual_ma_510300.example.yaml` with placeholders only.
   - Real machine config supplies account id, xtquant paths, QMT session/account identifiers, store paths, event paths, reconciliation tolerances, max pilot capital, and `allow_real_orders: false`.
   - Add `LiveStrategyConfig` and `load_live_strategy_config()` for `runtime_mode: live`.
   - Keep ordinary `load_strategy_config()` restricted to `runtime_mode: backtest | paper`, so non-live startup paths continue to reject live configs.

2. Extend `GatewayBase` lifecycle for true live gateways.
   - Add `connect(conf: Mapping[str, object]) -> None`, `close() -> None`, and `subscribe(symbols: list[str]) -> None`.
   - Add compatible `SimGateway` implementations and tests so existing Paper replay behavior is unchanged.
   - Keep all existing order, cancel, account, position, order snapshot, and trade snapshot methods stable.

3. Add `QmtGateway` behind `GatewayBase`.
   - Create `src/quant/live/gateway/qmt.py`.
   - Keep all xtquant imports inside this file.
   - Reuse the existing DTOs defined in `quant.core.contract` and re-exported by `quant.live.types`; do not create duplicate dataclasses for `OrderRequest`, `BrokerOrderSnapshot`, or `BrokerTradeSnapshot`.
   - Map xtquant account, positions, order snapshots, trade callbacks, submit, cancel, and query APIs into `Account`, `Position`, `BrokerOrderSnapshot`, and `BrokerTradeSnapshot`.
   - Add a durable order-reference model with a table or unique indexes for `local_order_id`, `client_order_ref`, `broker_order_id`, and `request_id`.
   - On submit, write a replayable client order reference that carries or resolves to the local `order_id`.
   - Persist the client/request reference before calling xtquant submit; persist `broker_order_id -> local order_id` as soon as the broker id is known.
   - Handle callback-before-return by parking early broker callbacks in an auditable pending-callback buffer until the local mapping is complete, then replaying them in order.
   - During reconnect query replay, resolve external broker ids through the stored mapping or client order reference before constructing `BrokerOrderSnapshot` / `BrokerTradeSnapshot`.
   - Handle reconnect query snapshots that contain only client reference, only request id, only broker order id, or repeated trade reports.
   - If a broker callback cannot be mapped to a known local order, do not fabricate an `order_id`; enter the existing safe failure path with an auditable reconciliation event.
   - Provide an explicit dry-run mode that exercises connect/query/subscribe without sending real orders.
   - Test real-broker callback hazards: duplicate trades do not double-book, terminal order states never regress, filled quantity never decreases, and reconnect replay does not rewrite already persisted facts.

4. Add a gateway factory for live runtime.
   - Extend `src/quant/live/gateway/factory.py` with a QMT builder.
   - Preserve existing SimGateway behavior for Paper.
   - Add tests that QMT factory fails closed when xtquant is unavailable.
   - `allow_real_orders: false` must still allow query-only/dry-run QMT gateway construction, but must block `send_order` and real-order CLI mode.

5. Add `scripts/run_live.py`.
   - Load strategy, live config, and global risk config.
   - Refuse to start unless the config says `runtime_mode: live`, the account id matches, and startup reconciliation passes.
   - Default command must be query-only/dry-run.
   - Query-only dry-run must not load strategy code, must not instantiate an order-capable execution path, and must not call `OrderManager.submit_order()`.
   - Query-only dry-run must leave no local orders or trades in SQLite.
   - Real order mode must require an explicit flag and a config-side opt-in.

6. Add explicit live snapshot initialization.
   - Provide a query-only initialization command for the first live run.
   - Allow initialization only when the local store is empty and has no orders or trades.
   - Require operator, reason, account-id confirmation, and precheck evidence.
   - Query broker account and positions, initialize the local account snapshot from broker truth, and append a JSONL event.
   - Normal live startup reconciliation must run after this initialization; it must continue to fail on an empty store.

**Exit criteria:**

- Unit tests cover config validation, gateway lifecycle compatibility, QMT DTO mapping, external-id mapping, callback-before-return handling, duplicate/out-of-order callback handling, factory failure modes, dry-run startup, query-only dry-run order isolation, and live snapshot initialization.
- `pytest -q`, `ruff check .`, `lint-imports`, and targeted `mypy` pass.
- Dry-run on the Windows QMT machine can connect, query account/positions/orders/trades, append events, and exit without submitting orders.

## M4b: Windows Deployment And Recovery

**Purpose:** Make the live process operable on the actual QMT host before any pilot order is allowed.

**Tasks:**

1. Write `docs/runbooks/qmt_live_runbook.md`.
   - Include install, QMT login, xtquant version capture, config validation, pre-open startup, close reconciliation, manual halt/resume, emergency broker-client fallback, and incident notes.

2. Add deployment files.
   - Create a Windows service/NSSM example under `deploy/windows/`.
   - Add a pre-open self-check command that verifies QMT connectivity, NTP clock health, latest local data date, account id, config snapshot, writable store/events paths, and alert channel.

3. Add backup and restore drill docs.
   - Back up `meta.db`, `events.jsonl`, config snapshots, and alert delivery receipts after each live day.
   - Restore the backup in a clean directory and verify startup reconciliation behavior.

4. Add live ops evidence.
   - Extend or mirror the M3b signoff validator for M4 pilot evidence.
   - Validate trading dates against the project trade calendar.
   - Require strictly increasing dates and a window span that covers at least 2 calendar weeks for pilot signoff.
   - Verify referenced reconciliation, alert, restart, and broker-order event sequence ids exist in the archived JSONL event journal.
   - Require restart drill evidence and close reconciliation evidence before enabling pilot orders.

**Exit criteria:**

- Windows dry-run can be started through the documented service command and stopped cleanly.
- Restart drill proves the process starts, queries broker state, reconciles, and stays safe.
- Backup restore drill is recorded before pilot order mode is enabled.

## M4c: Small-Capital Pilot Gate

**Purpose:** Run the first real-money pilot with deliberately small risk and explicit daily acceptance.

**Tasks:**

1. Enable real orders only for the pilot config.
   - `allow_real_orders: true` must be config-side and command-side.
   - `max_order_value`, `max_position_value_per_symbol`, `max_gross_exposure_pct`, and daily loss thresholds must be stricter than Paper defaults.
   - Live reconciliation defaults must set `auto_repair_cash_drift_below: 0`.
   - If a live reconciliation ever records `REPAIRED`, that day does not count toward the pilot window unless it has an incident note, operator approval, and explicit signoff inclusion.

2. Run a pilot observation window of at least 10 counted trading days that spans at least 2 calendar weeks.
   - Daily pre-open startup reconciliation.
   - Daily close reconciliation with zero unresolved difference.
   - Counted-day rules inherit M3b: any day with an unresolved engine crash, unresolved reconciliation difference, missing event journal, missing SQLite state, or unapproved `REPAIRED` reconciliation does not count.
   - At least one active restart drill.
   - At least one CRIT alert drill visible on the phone-side channel.
   - No unresolved manual intervention.

3. Produce M4 pilot signoff.
   - Include counted trading days, calendar span, order/trade count, rejected orders, reconciliation sequence ids, alert sequence ids, restart drill, backup restore drill, incidents, event journal path, and final operator signoff.

**Exit criteria:**

- Pilot runs at least 10 counted trading days across at least 2 calendar weeks with no unresolved reconciliation difference and no unapproved `REPAIRED` reconciliation.
- Every real order can be traced from strategy intent to risk decision, OMS order, broker order id, trade callback, SQLite state, and JSONL event.
- Any incident has a written cause and follow-up before capital is increased.

## Recommended Task Order

1. Complete M4-0: harden M3b validator, update signoff template, add tests, and add live config ignore coverage.
2. Validate the real M3b signoff artifact and confirm QMT work is no longer blocked.
3. Commit and tag the completed M3 state.
4. Write M4 live config schema and tests.
5. Add GatewayBase lifecycle tests and SimGateway compatibility methods.
6. Implement QMT external-id mapping, DTO mapping, and callback idempotency tests with fake xtquant payloads.
7. Implement `QmtGateway` dry-run connect/query/subscribe behavior.
8. Add live runner with fail-closed startup checks and explicit live snapshot initialization.
9. Run the full local quality gate.
10. Write the minimum Windows dry-run runbook and pre-open self-check command.
11. Move to the Windows QMT machine and run dry-run verification by following the runbook.
12. Execute restart drill and backup restore drill; append evidence to the runbook/signoff artifact.
13. Enable small pilot orders only after all M4a/M4b evidence is present.
14. Run M4c observation and sign off before any capital increase.

## Definition Of Done For M4-0

- [ ] M3b signoff template includes event journal and trade calendar paths.
- [ ] M3b validator accepts at least 10 counted trading days and a declared counted window; extra observation days are allowed.
- [ ] M3b validator checks trade calendar membership and strictly increasing dates.
- [ ] M3b validator verifies referenced reconciliation, disconnect, recovery, and CRIT event seq values exist in the archived JSONL event journal.
- [ ] M3b validator checks referenced event semantics: event type, status, startup flag, date, account id, strategy id, run id, CRIT severity, and delivery id.
- [ ] Hardened M3b validator tests pass.
- [ ] `config/live/local/` or equivalent real live overlay path is gitignored before any committed live config example is added.
- [ ] Real M3b evidence validates and the M3 state is committed and tagged before QMT work starts.

## Definition Of Done For M4a

- [ ] QMT SDK imports exist only in `src/quant/live/gateway/qmt.py`.
- [ ] `GatewayBase` exposes `connect`, `close`, and `subscribe`, with compatible SimGateway implementations.
- [ ] `runtime_mode: live` is accepted only by `LiveStrategyConfig` / `load_live_strategy_config()`.
- [ ] Ordinary `load_strategy_config()` still rejects `runtime_mode: live`.
- [ ] Strategies still import only `quant.core.contract`.
- [ ] QMT account, position, order, and trade snapshots are mapped into existing internal DTOs with tests; no duplicate DTO dataclasses are introduced.
- [ ] Durable order-reference storage has unique mappings for `local_order_id`, `client_order_ref`, `broker_order_id`, and `request_id`.
- [ ] QMT submit writes a replayable client order reference that resolves to local `order_id`.
- [ ] Client/request reference is persisted before xtquant submit; `broker_order_id -> local order_id` mapping is persisted before callbacks reach OMS.
- [ ] Callback-before-return is covered by a pending-callback buffer and deterministic replay into OMS after mapping completes.
- [ ] Reconnect query replay resolves external broker ids before constructing internal broker snapshots.
- [ ] Reconnect query replay handles snapshots containing only client ref, only request id, only broker order id, or repeated trade reports.
- [ ] Duplicate trades do not double-book.
- [ ] Terminal order states never regress.
- [ ] Filled quantity never decreases.
- [ ] Reconnect replay does not rewrite already persisted facts.
- [ ] Dry-run mode cannot submit real orders.
- [ ] `allow_real_orders: false` permits query-only/dry-run startup and blocks all real order submission paths.
- [ ] Query-only dry-run does not load strategy code, does not call `OrderManager.submit_order()`, and leaves no orders or trades in SQLite.
- [ ] First live snapshot initialization is an explicit query-only command, requires operator/precheck evidence, writes a JSONL event, and only works on an empty store.
- [ ] Normal live startup reconciliation still fails on an empty store before explicit initialization.
- [ ] Startup reconciliation must pass before strategy orders are accepted.
- [ ] `pytest -q`, `ruff check .`, `lint-imports`, targeted `mypy`, and Paper replay regression pass.

## Definition Of Done For M4b

- [ ] Windows QMT host runbook exists and has been followed.
- [ ] QMT/xtquant version and broker account id are recorded outside Git secrets.
- [ ] NSSM or equivalent service command starts and stops the live process.
- [ ] Restart drill proves safe recovery through reconciliation.
- [ ] Backup restore drill succeeds in a clean directory.
- [ ] CRIT alert reaches the phone-side channel with run id, strategy id, account id, event seq, local time, and market time.
- [ ] M4 evidence validator checks trade calendar membership, strictly increasing dates, minimum calendar span, and event sequence traceability.
- [ ] Live reconciliation config defaults `auto_repair_cash_drift_below` to `0`, or any `REPAIRED` day is excluded unless incident-reviewed and explicitly included in signoff.

## Definition Of Done For M4c

- [ ] Pilot capital limit is explicit, small, and stored only in gitignored local config or machine secrets.
- [ ] Real order mode requires both config and CLI opt-in.
- [ ] Pilot runs at least 10 counted trading days across at least 2 calendar weeks with daily startup and close reconciliation.
- [ ] Every counted day has zero unresolved reconciliation difference.
- [ ] Any `REPAIRED` reconciliation is either excluded from counted days or has incident note, operator approval, and explicit signoff inclusion.
- [ ] At least one restart drill and one CRIT alert drill are completed during the pilot.
- [ ] No unresolved manual intervention remains.
- [ ] Capital increase remains blocked until the M4 pilot signoff is complete.

## First Iteration Recommendation

The next concrete iteration should be **M4-0 only**: harden M3b evidence validation, update the signoff template, add tests, and add live local config ignore coverage. After M4-0 validates the real M3b signoff, the next QMT iteration should be **M4a only**: live config schema, QMT adapter dry-run, live runner, and tests. Do not enable real orders in the first QMT iteration.
