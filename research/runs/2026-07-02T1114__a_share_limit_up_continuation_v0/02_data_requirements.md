# Data Requirements - A-Share Limit-Up Continuation v0

Status: DRAFT
Run ID: `2026-07-02T1114__a_share_limit_up_continuation_v0`
Strategy ID: `a_share_limit_up_continuation_v0`
Intended mode: research-only

## Intended Use

This data is needed to decide whether the limit-up continuation thesis is even researchable. It is not approved for formal backtest validation, paper trading, QMT integration, broker integration, or real-money trading.

Daily data may support a next-session continuation event study. Daily data is not sufficient to claim same-day limit-up board-capture buyability.

## Required Datasets

| Dataset | Symbols | Frequency | Required fields | Source | Date range | Calendar | Adjustment | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| instruments | Shanghai/Shenzhen A-share common stocks | n/a | symbol, name, exchange, board, listing_date, delisting_date, ST flag, suspension status, listing status | NOT_SELECTED | enough to cover full event study | exchange sessions | n/a | NOT_STARTED |
| daily_bars | same as audited instruments | daily | open, high, low, close, volume, amount, turnover, timestamp | NOT_SELECTED | preferably 2016-01-01 through latest reproducible snapshot, or longer if reproducible | A-share exchange calendar | raw prices plus explicit adjusted close policy | NOT_STARTED |
| price_limits | same as audited instruments | daily | limit_up_price, limit_down_price, rule source, special-rule flag | NOT_SELECTED | same as daily_bars | A-share exchange calendar | raw trading prices | NOT_STARTED |
| corporate_actions | same as audited instruments | event/date | adjustment factor, split, dividend, effective date | NOT_SELECTED | same as daily_bars | A-share exchange calendar | explicit factor methodology | NOT_STARTED |
| market_breadth | A-share market and board groups | daily | advancers, decliners, limit-up count, limit-down count, amount, turnover | NOT_SELECTED | same as daily_bars | A-share exchange calendar | n/a | NOT_STARTED |
| sector_breadth | industry or concept groups | daily | sector returns, breadth, amount, turnover, limit-up count | NOT_SELECTED | same as daily_bars | A-share exchange calendar | n/a | NOT_STARTED |
| intraday_or_orderbook | audited subset only | minute/tick/order-book | timestamp, price, volume, amount, bid/ask or auction/queue proxy | NOT_SELECTED | required only for board-capture experiment | A-share exchange calendar | raw trading prices | NOT_STARTED |

## Quality Requirements

- Data source must be named and reproducible.
- Retrieval date, provider version where applicable, row counts, and hashes or manifests must be recorded.
- Timestamps must document timezone and session semantics.
- Limit-up detection must use raw trading prices and board-specific price-limit rules.
- ST status, special-treatment status, IPO/new-listing exceptions, suspensions, delistings, and board classifications must be explicit.
- Missing, duplicate, stale, future, or repaired records must be measurable.
- Survivorship-bias handling must be reviewed before any cross-sectional claims.
- Calendar and corporate-action assumptions must match the strategy frequency.

## Execution Data Boundary

The research must not use daily high equals limit-up as proof that a buy order could fill at or near the limit-up price.

For same-day board-capture research, the data must support at least one of:

- minute-level path showing when the price first reached limit-up and whether it reopened;
- auction and transaction detail showing executable volume;
- order-book or queue proxy sufficient to model failed entries;
- a conservative assumption that unfilled entries are skipped and filled entries require strong evidence.

If these are unavailable, the only acceptable first experiment is next-session continuation after a prior-day limit-up event.

## Reproducibility Requirements

Data snapshot path: blocked until source selection
Dataset manifest path: blocked until source selection
Build command: blocked until source selection
Provider version or retrieval date: blocked until source selection
Hash or row counts: blocked until source selection

## Known Gaps

- No A-share individual-stock dataset has been selected.
- No intraday, tick, or order-book dataset has been selected.
- No audited price-limit rule mapping has been created.
- No survivorship-bias policy has been reviewed.
- No data audit has been run.

## Data Audit Handoff

Data audit owner: `data-audit-reviewer`
Audit template: repo data audit review format
Expected audit output: `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`
Next action: select candidate data sources, build a reproducible data manifest, then run data-audit review before any performance claim.
