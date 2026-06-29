# Strategy Thesis - ETF Regime Rotation v1

Status:

`THESIS_DRAFT`

Strategy identity:

- Name: ETF regime rotation v1
- Asset universe: `510300.SH`, `510500.SH`
- Bar frequency: daily bars
- Holding horizon: multi-day to multi-week, constrained by `min_hold_days: 5`
- Intended mode: research only
- Existing research config: `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation_510300_510500.yaml`
- Existing research code: `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation.py`

Hypothesis:

If broad China A-share ETF leadership alternates between large-cap exposure (`510300.SH`) and mid/small-cap exposure (`510500.SH`), then a daily trend-filtered relative-momentum rotation rule may improve drawdown-adjusted participation versus a single ETF exposure, because it avoids candidates trading below their trend baseline and only allocates to the stronger eligible ETF.

Evidence:

- Observed repository evidence:
  - The research strategy ranks `510300.SH` and `510500.SH` by recent momentum when price is above a trend moving average.
  - The strategy uses `ctx.now` for switch timing and does not use detected system time.
  - The strategy imports `quant.core.contract` and stdlib only; no detected imports from `quant.data`, `quant.backtest`, `quant.live`, `quant.risk`, or `ops`.
  - The inspected backtest artifact contains `orders.csv`, `trades.csv`, `equity.csv`, `events.jsonl`, `report.md`, and `config_snapshot.yaml`.
  - The inspected backtest has 25 orders, 25 trades, 518 equity rows, and 50 event lines.
  - Existing report records final value `120098.3` from initial cash `100000`.
- Existing contradictory or limiting evidence:
  - The inspected period is short, roughly one year.
  - Existing iteration note says the result did not beat `510500` buy-and-hold in the same period.
  - There is no formal data audit conclusion yet.
  - There is no formal backtest-validator conclusion yet.
  - There is no formal risk-governor conclusion yet.
  - There is no paper observation for this strategy.

Assumptions:

- Data assumption: AKShare-derived ETF daily bars, trade calendar, instruments, and adjustment factors are sufficiently complete for initial research after a formal data audit.
- Execution assumption: daily-bar close/next-session style execution and two-step switching can be represented credibly by the existing backtest engine and cost model.
- Regime assumption: relative strength between `510300.SH` and `510500.SH` persists long enough to survive daily-bar costs, slippage, and T+1-like switching constraints.
- Capacity/liquidity assumption: the tested notional remains small relative to ETF liquidity; this must be verified before any paper discussion.
- Risk assumption: independent risk controls, not strategy-internal checks, can cap order value, position value, gross exposure, drawdown, and market-data staleness.

Falsifiers:

- Data falsifier: data audit finds unclear source lineage, missing sessions, duplicate bars, inconsistent calendars, bad adjustment factors, or future-data leakage.
- Backtest falsifier: after realistic costs and artifact review, returns are driven by one regime, few trades, lookahead, parameter overfit, benchmark underperformance, or unstable sample splits.
- Paper falsifier: paper events, reconciliation, or alert evidence are missing, non-reproducible, or show unresolved manual intervention.
- Risk falsifier: strategy behavior can bypass `quant.risk`, exceed configured exposure/order limits, create unresolved rejected orders, or require risk limits to be loosened.
- Time/regime falsifier: out-of-sample or longer-history tests show no durable benefit versus simpler baselines such as buy-and-hold, cash-filtered single ETF, or dual moving average.

Data needed:

- Longer reproducible ETF daily dataset for `510300.SH` and `510500.SH`.
- Trade calendar aligned to the exchange sessions used by the bars.
- Instrument metadata with lot size, quantity step, exchange, listing status, and delisting status.
- Adjustment factors with clear source and effective-date semantics.
- Data build logs or hashes sufficient to reproduce the dataset.
- Benchmark series for `510300.SH`, `510500.SH`, equal-weight hold, and cash/no-position baseline.

Validation path:

1. Run `data-audit-reviewer` on the ETF rotation dataset and source lineage.
2. If data audit passes, run backtest artifact review with `backtest-validator`; do not treat profitability as proof.
3. Require sample split and sensitivity checks before paper discussion: longer history, multiple windows, cost sensitivity, and benchmark comparisons.
4. If backtest review passes, run `risk-governor` against strategy config and independent risk limits.
5. Only after thesis, data, backtest, and risk reviews pass, consider paper observation. Any M4/QMT/live-adjacent step remains blocked until `paper-live-gatekeeper` and human decision.

Next decision:

`THESIS_DRAFT` accepted for research tracking. Next loop should route to `data-audit-reviewer` before any new backtest claims or paper discussion.

Not allowed:

This thesis is not investment advice, not an investment recommendation, not paper approval, and not trading permission.

