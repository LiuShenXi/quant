# M3b Paper Observation Checklist

M3a means the local deterministic Paper replay infrastructure is implemented and tested. M3b is the真钱前 Paper gate from the roadmap. M4 is blocked until this checklist is complete.

## Required Window

- Run the same strategy config in `runtime_mode: paper` for at least 10 trading days.
- Record one row per trading day: date, strategy id, account id, final engine state, order count, trade count, reject count, reconciliation status, alerts, and operator notes.
- Any day with an unresolved engine crash, unresolved reconciliation difference, or missing event journal does not count toward the 10 trading days.

## Daily Acceptance

- Pre-open startup reconciliation completes before strategy orders are accepted.
- Close reconciliation reports daily reconciliation zero difference.
- No unresolved manual intervention remains at end of day.
- `runtime/paper/events.jsonl` and `runtime/paper/meta.db` are archived.

## Required Drill

- Perform at least one disconnect drill during the observation window.
- Expected behavior: gateway disconnect moves state to `FREEZE_OPEN`, emits a CRIT alert, blocks opening orders, reconnects, runs reconciliation, and resumes only after reconciliation passes.

## Alert Acceptance

- Perform one CRIT alert delivery drill.
- The delivered alert must include `run_id`, `strategy_id`, `account_id`, `last_event_seq`, `local_time`, and `market_time`.
- Confirm the alert is visible on the configured phone-side channel.

## Final M3b Sign-Off

- 10 trading days completed.
- daily reconciliation zero difference on every counted day.
- disconnect drill completed.
- CRIT alert delivery confirmed.
- no unresolved manual intervention remains.
- M4 is blocked until this checklist is complete.
