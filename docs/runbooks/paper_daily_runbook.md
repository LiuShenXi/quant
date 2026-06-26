# Paper Daily Runbook

## Current Real-Data Validation Path

Use this path for the current `510300.SH` non-money validation:

```text
strategy: config/strategies/dual_ma_510300_real_validation_paper.yaml
paper: config/paper_real_510300.yaml
risk: config/risk/global.yaml
data_root: data_real/etf_510300_2025_2026_check/
runtime: runtime/paper_real_510300/
ledger: 首轮量化使用记录/原始记录/observations/paper_daily_ledger.csv
```

Same-day daily bars are accepted only after `15:10` Asia/Shanghai. Before that time, a
refresh may be run as a health check, but the row must not be counted for M3b.

## 08:45 Pre-Open

- Pull latest code and confirm `pytest -q`, `ruff check .`, and `lint-imports` pass.
- Confirm `config/strategies/*_paper.yaml` uses `runtime_mode: paper`.
- Remove stale local runtime state only for deliberate dry runs; never delete state during a continuity test.
- Start Paper replay with `python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml`.
- For the current real-data validation path, use `.venv/bin/python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_real_validation_paper.yaml --paper config/paper_real_510300.yaml --risk config/risk/global.yaml`.
- Check `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status`; expected `NORMAL`.
- For the current real-data validation path, check `.venv/bin/python scripts/ops.py --store runtime/paper_real_510300/meta.db --events runtime/paper_real_510300/events.jsonl --operator shenxi status`; expected `NORMAL`.

## During Session

- Any `CRIT` alert requires checking `runtime/paper/events.jsonl` and `runtime/paper/meta.db`.
- Do not resume from `HALT` until account, positions, active orders, and last event sequence have been inspected.
- Use `freeze-open` for manual caution and `halt` for unknown state.

## 15:05 Close

- Confirm no active orders remain unless they are intentionally carried by the simulator.
- Run reconciliation from the engine or next startup.
- Archive `runtime/paper/meta.db`, `runtime/paper/events.jsonl`, and the strategy config snapshot.
- For the current real-data validation path, wait until `15:10` Asia/Shanghai, refresh `510300.SH` through the current trade date, confirm the latest bar is the current date at `15:00`, then archive `runtime/paper_real_510300/meta.db` and `runtime/paper_real_510300/events.jsonl`.
- Append a counted ledger row only when the final state is `NORMAL`, reconciliation is `OK`, cash difference is `0.0`, there are no active orders, the event journal exists, and no unresolved manual intervention remains.

## Acceptance Log

- M3b requires at least 10 trading days of Paper observation before M4 planning.
- Each counted day must record daily reconciliation zero difference.
- The observation window must include one disconnect drill.
- The observation window must include verified CRIT alert delivery.
- The gate requires no unresolved manual intervention.
- Required daily notes: date, strategy id, final state, orders, trades, rejects, reconciliation result, alerts.

## Final Sign-Off Intake

- Produce an operator-authored `m3b_signoff.yaml` after the full observation window is complete.
- Keep the referenced Paper `events.jsonl` archive and trade calendar beside the signoff package or use absolute paths.
- Run `python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml`.
- Only output containing `M4a may start` opens the M4a/QMT gate; any rejection keeps M4a blocked.
