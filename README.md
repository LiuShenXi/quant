# Personal Quant Platform

First slice: A股 ETF daily-bar credible backtest platform.

This repository intentionally excludes QMT, real broker gateways, real-money trading, minute bars, and web UI.

## Current Phase

M0-M2 implements a credible A股 ETF daily-bar backtest slice. M3 adds Paper trading
infrastructure only; real broker gateways and real-money trading remain deliberately
excluded.

M3 has two Paper-only phases:

- M3a is deterministic local Paper replay.
- M3b is the real-money-pre-gate observation process. It requires 10 trading days,
  daily reconciliation zero difference, one disconnect drill, verified CRIT alert
  delivery, and no unresolved manual intervention.

M4 remains blocked until the M3b gate is complete.

## M3b Sign-Off Intake

The blocking artifact is an operator-authored `m3b_signoff.yaml` package. It must
reference the archived Paper `events.jsonl` and trade calendar used for the 10
counted trading days.

Validate the package before starting any M4a/QMT work:

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

Expected success output includes `M4a may start`. Any rejection means M4a remains
blocked.

## Phase Language

M3a is the local deterministic Paper replay implementation. M3b is the真钱前 Paper observation gate: 10 trading days, daily reconciliation zero difference, one disconnect drill, and CRIT alert delivery confirmed. M4 remains blocked until M3b is signed off.

## Paper Mode

After M3 is implemented:

```bash
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status
```

Live config examples may contain placeholders only. Real local overlays belong in
`config/live/local/`, which is gitignored and must not be committed.

## Documents

- `架构包/`: original architecture package.
- `codex_修改后架构/`: revised architecture package and M0-M2 development plan.
