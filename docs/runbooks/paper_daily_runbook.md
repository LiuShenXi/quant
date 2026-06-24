# Paper Daily Runbook

## 08:45 Pre-Open

- Pull latest code and confirm `pytest -q`, `ruff check .`, and `lint-imports` pass.
- Confirm `config/strategies/*_paper.yaml` uses `runtime_mode: paper`.
- Remove stale local runtime state only for deliberate dry runs; never delete state during a continuity test.
- Start Paper replay with `python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml`.
- Check `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status`; expected `NORMAL`.

## During Session

- Any `CRIT` alert requires checking `runtime/paper/events.jsonl` and `runtime/paper/meta.db`.
- Do not resume from `HALT` until account, positions, active orders, and last event sequence have been inspected.
- Use `freeze-open` for manual caution and `halt` for unknown state.

## 15:05 Close

- Confirm no active orders remain unless they are intentionally carried by the simulator.
- Run reconciliation from the engine or next startup.
- Archive `runtime/paper/meta.db`, `runtime/paper/events.jsonl`, and the strategy config snapshot.

## Acceptance Log

- M3b requires at least 10 trading days of Paper observation before M4 planning.
- Each counted day must record daily reconciliation zero difference.
- The observation window must include one disconnect drill.
- The observation window must include verified CRIT alert delivery.
- The gate requires no unresolved manual intervention.
- Required daily notes: date, strategy id, final state, orders, trades, rejects, reconciliation result, alerts.
