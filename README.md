# Personal Quant Platform

First slice: A股 ETF daily-bar credible backtest platform.

This repository intentionally excludes QMT, real broker gateways, real-money trading, minute bars, and web UI.

## Current Phase

M0-M2 implements a credible A股 ETF daily-bar backtest slice. M3 adds Paper trading infrastructure only; real broker gateways and real-money trading remain deliberately excluded.

## Paper Mode

After M3 is implemented:

```bash
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status
```

## Documents

- `架构包/`: original architecture package.
- `codex_修改后架构/`: revised architecture package and M0-M2 development plan.
