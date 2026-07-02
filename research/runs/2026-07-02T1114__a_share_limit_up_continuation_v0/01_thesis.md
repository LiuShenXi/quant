# Strategy Thesis - A-Share Limit-Up Continuation v0

Status: THESIS_DRAFT
Strategy ID: `a_share_limit_up_continuation_v0`
Run ID: `2026-07-02T1114__a_share_limit_up_continuation_v0`
Mode: research-only

## Hypothesis

If A-share individual stocks hit limit-up under favorable market breadth, sector strength, liquidity, and board-quality conditions, then next-session or 1-3 session continuation returns may improve versus unconditional limit-up events because attention, crowding, and order imbalance can persist briefly.

## Evidence

- Observed market behavior: user-provided market intuition that short-term A-share limit-up opportunities may compound quickly.
- Prior research or source: no reviewed source in this repository yet.
- Backtest evidence: none.
- Paper evidence: none.
- Contradictory evidence: not yet measured; known concerns include failed entry, failed exit, T+1 constraints, price-limit lockups, crowding, high turnover, slippage, and regime decay.

## Assumptions

- Data assumption: the selected dataset can correctly identify real limit-up events, board-specific limit prices, ST status, IPO or special-rule periods, suspensions, delistings, corporate actions, and survivorship bias.
- Execution assumption: modeled entries and exits are realistically achievable after fees, taxes, slippage, queue failure, failed entry, failed exit, and T+1 plus price-limit constraints.
- Regime assumption: any continuation effect is not limited to one bull-market or mania window.
- Capacity or liquidity assumption: trade size remains small enough relative to amount, turnover, and available liquidity that the simulated fill assumptions remain plausible.
- Risk assumption: independent risk controls can cap single-name exposure, cluster exposure, event-day loss, drawdown, and halt/freeze conditions outside strategy logic.

## Falsifiers

- Data falsifier: limit-up events, ST status, board rules, suspensions, listing windows, or corporate actions cannot be reproduced and audited.
- Backtest falsifier: the edge disappears after realistic costs, failed-entry/failed-exit assumptions, or sample/regime splits.
- Paper falsifier: later paper observation shows signals cannot be executed, reconciled, or audited without manual intervention.
- Risk falsifier: drawdown, gap risk, liquidity lockup, concentrated event clusters, or single-name exposure cannot pass independent risk review.
- Time or regime falsifier: the effect only exists in a narrow historical mania period or vanishes in more recent out-of-sample windows.

## Data Needed

- Symbols or instruments: Shanghai and Shenzhen A-share individual stocks, initially excluding ST, newly listed, suspended, delisting-risk, and special-rule securities until explicit data handling exists.
- Frequencies: daily for first-pass event study; minute or tick/order-book data before any same-day board-capture research.
- Fields: symbol, exchange, board, listing date, delisting date, ST status, suspension status, open, high, low, close, volume, amount, turnover, limit-up price, limit-down price, adjustment factor, sector or industry, market breadth, and sector breadth.
- Calendar: exchange trading sessions, holidays, suspensions, and timezone policy.
- Adjustment or corporate action handling: explicit raw price versus adjusted price policy; limit-up detection must use the correct raw trading prices and rule-adjusted limits.
- Data source evidence: provider name, retrieval date, provider version where applicable, row counts, hashes or manifests, and exchange-rule references.

## Validation Path

1. Keep this thesis as `THESIS_DRAFT`.
2. Select candidate data sources and write a data-audit triage.
3. Run `data-audit-reviewer` before formal event results.
4. Design a minimal event-study backtest with declared costs and execution assumptions.
5. Run `backtest-validator` only after artifacts exist.
6. Run `risk-governor` before any paper-observation discussion.
7. Keep paper/live/QMT/money stages blocked unless every prior gate passes and the user separately authorizes stage advancement.

## Next Decision

Status: THESIS_DRAFT

Next decision: choose an auditable A-share data source and decide whether this strategy starts with daily next-session continuation only, or whether intraday board-capture data is available enough to define a separate stricter experiment.

This document is not investment advice, investment recommendation, paper approval, live approval, or trading permission.
