# CIO Decision Package - A-Share Limit-Up Continuation v0

CIO Decision: RESEARCH_ONLY_THESIS_DRAFT

## Strategy Opportunity

The candidate studies whether A-share individual-stock limit-up events contain a short-horizon continuation effect after accounting for execution feasibility, costs, failed entries, failed exits, T+1 constraints, price-limit lockups, liquidity, and regime dependence.

The opportunity is researchable. It is not approved for paper, live, QMT, broker integration, or real-money trading.

## Recommended Next Action

Select auditable data sources and run a data-audit triage before any performance claim.

The first research path should be daily next-session continuation, not same-day board capture. Same-day board capture is blocked until intraday or order-book data exists.

## Candidate Strategies

- `a_share_limit_up_continuation_v0_daily`: identify prior-day limit-up events and test next-session to 3-session continuation under predefined filters.
- `a_share_limit_up_board_capture_v0_intraday`: separate stricter candidate for same-day board capture; blocked until intraday or order-book data exists.

## Evidence Reviewed

- User described the strategy idea on 2026-07-02.
- Repository constitution and promotion workflow require thesis, data audit, backtest validation, and risk review before paper discussion.
- No audited dataset, backtest artifact, risk review, or paper evidence exists.

## Experiments To Run

- Data-source selection and data-audit triage.
- Daily event baseline.
- Quality-filter analysis with thresholds fixed before performance review.
- Cost, failed-entry, and failed-exit stress.
- Sample split and regime split.
- Benchmark ablation against simple momentum, high-volume, and sector-matched baselines.

## Sub-Agent Routing

- `strategy-thesis-tracker`: used; current result is `THESIS_DRAFT`.
- `data-audit-reviewer`: next required gate after data-source selection.
- `backtest-validator`: blocked until data audit and reproducible artifacts exist.
- `risk-governor`: blocked until a candidate backtest and risk configuration exist.
- `paper-live-gatekeeper`: not applicable; paper/live/QMT/money stages are blocked.

## Improvement Proposal

Reframe the user's original "快速滚雪球" wording into a safer research question:

Can a limit-up event family produce a reproducible, cost-aware, risk-bounded short-horizon return distribution?

This keeps the thesis falsifiable and prevents strategy excitement from weakening evidence requirements.

## Risk Authorization Needed

No capital authorization is needed because the strategy remains research-only.

Human authorization would be required before:

- adding this candidate to a formal implementation queue;
- selecting data sources with paid or credentialed access;
- creating paper configuration;
- changing risk boundaries;
- discussing QMT, broker, or real-money stages.

## Blocking Issues

- No audited A-share individual-stock dataset.
- No audited price-limit rule mapping.
- No intraday or order-book data for same-day board capture.
- No backtest artifacts.
- No independent risk review.
- No paper observation.

## Default Safe Option

Keep `a_share_limit_up_continuation_v0` research-only. The next safe step is data-source selection and data audit, not trading logic.

## Not Allowed

- Do not paper trade this candidate.
- Do not trade live.
- Do not connect QMT or a broker.
- Do not create real orders.
- Do not use real credentials, account identifiers, broker tokens, or live overlays.
- Do not describe this package as investment advice, investment recommendation, or trading permission.
