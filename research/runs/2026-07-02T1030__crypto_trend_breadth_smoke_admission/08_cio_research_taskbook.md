# CIO Research Taskbook - Crypto Trend Breadth Top2

CIO Decision: `CRYPTO_RESEARCH_TASKBOOK_LOCKED`

Status: `RESEARCH_ONLY`

This taskbook is a business research mandate. It does not approve paper,
exchange connectivity, live trading, broker work, QMT, real orders, or real
money use.

## Classification

- Request type: strategy construction and continuous research optimization.
- Scope: research-only crypto spot strategy admission.
- Primary candidate: `crypto_trend_breadth_top2_v1`.
- Current stage: synthetic smoke passed with warnings; real data and formal
  backtest remain blocked.
- Default safe option: keep the strategy in research until data, backtest, and
  risk gates pass in order.

## Research Objective

Decide whether `crypto_trend_breadth_top2_v1` deserves a formal historical
backtest review after data audit.

The objective is not to prove an edge today. The objective is to pre-commit the
business question, baselines, ablations, success criteria, and kill criteria so
the future real-data run is judged by a stable standard.

## Thesis Review

Status: `THESIS_UPDATE`

Hypothesis:

If BTC, ETH, and SOL show persistent trend regimes and cross-sectional
leadership, then a daily trend breadth filter plus 4h top-two rotation may
participate in crypto upside while reducing severe drawdowns versus passive
crypto exposure.

Evidence:

- Parent thesis exists in the 2026-07-01 admission package.
- Strategy implementation and synthetic smoke artifacts exist.
- Binance Spot REST probe succeeded as a source probe.
- No audited real crypto dataset exists.
- No formal historical crypto backtest exists.

Most important assumption:

The market thesis depends on clean, venue-specific, reproducible BTCUSDT,
ETHUSDT, and SOLUSDT spot bars. Synthetic smoke cannot support market
conclusions.

Falsifiers:

- Data audit fails and the issue cannot be resolved or documented.
- Formal backtest max drawdown exceeds 35% under the declared cost model.
- Equal-weight BTC/ETH/SOL is not materially worse on drawdown after costs.
- Results depend mainly on one asset, one short regime, or too few trades.
- Cost stress destroys the apparent advantage.
- Cash, fee, or sizing behavior creates recurring negative cash or unreviewed
  leverage.

Next decision:

`VALIDATE_REAL_CRYPTO_DATASET_THEN_RUN_PRECOMMITTED_MATRIX`

## Frozen Candidate Set

Primary strategy:

- `crypto_trend_breadth_top2_v1`.

Allowed baselines:

- Stablecoin cash.
- BTC buy-and-hold.
- ETH buy-and-hold.
- SOL buy-and-hold.
- BTC/ETH/SOL equal-weight.

Allowed ablations:

- Top2 rotation without breadth filter.
- Top2 rotation without portfolio stop.
- Top2 rotation without cooldown.
- Equal-weight with the same breadth filter.

Not allowed before the first formal matrix:

- New crypto assets.
- Parameter search for best-looking windows.
- New entry/exit logic.
- Leverage or derivatives.
- Paper/live configuration.

## Precommitted Experiment Matrix

| Phase | Question | Required comparison | CIO decision use |
| --- | --- | --- | --- |
| Data admission | Is the dataset fit for research backtest? | Binance bars versus manifest, hashes, quality report, and sanity source | Block or allow formal backtest generation |
| Baseline backtest | Does the full strategy beat simple exposure on drawdown-adjusted terms? | Full strategy versus cash, single-asset holds, and equal-weight | Decide whether the thesis remains alive |
| Cost stress | Does the result survive explicit fee and slippage assumptions? | Base cost versus stressed cost | Detect fragile turnover-driven effects |
| Ablation | Which component carries the result? | Full strategy versus no-breadth, no-stop, no-cooldown, equal-weight breadth | Decide whether the rule set is coherent |
| Regime split | Is performance concentrated in one market state? | Calendar-year and bull/bear/chop slices | Detect one-regime dependence |
| Asset attribution | Is the result mostly SOL or one winner? | Contribution by BTC, ETH, SOL | Detect hidden single-asset bet |
| Trade distribution | Is evidence broad enough? | Trade count, holding periods, win/loss concentration | Detect too-few-trades risk |
| Cash and sizing | Does execution stay internally valid? | Cash floor, fees, rejected orders, event log | Block risk review if accounting is unstable |

## Promotion Rules

The strategy may advance from research-only data work to formal backtest review
only if:

- `data-audit-reviewer` returns `PASS` or an explicitly accepted
  `PASS_WITH_WARNINGS`.
- Dataset source, UTC semantics, symbols, date range, build command, hashes,
  and quality report are archived.
- The end-boundary behavior found in the Binance probe is resolved in the
  formal data contract.
- The run uses the frozen candidate set and experiment matrix above.

The strategy may advance from formal backtest review to risk review only if:

- `backtest-validator` returns `PASS` or an explicitly accepted
  `PASS_WITH_WARNINGS`.
- Artifacts include config snapshot, manifest, orders, trades, equity,
  events, and report.
- Costs, slippage, execution timing, and benchmarks are declared.
- Negative cash or fee-overdraft behavior is either eliminated or documented as
  a blocker.

The strategy may not advance to paper observation without independent risk
review. Paper/live/QMT/broker/real-money stages remain blocked unless the full
promotion workflow is satisfied and a human decision is made.

## Kill Or Hold Criteria

Retire or demote the candidate if:

- Formal data audit cannot pass.
- Max drawdown is above 35% under realistic costs.
- Equal-weight BTC/ETH/SOL dominates on both return and drawdown.
- The full strategy only works because of one asset or one narrow regime.
- Ablations show the headline logic is not responsible for the result.
- Cost stress makes the strategy economically indistinguishable from cash or
  worse than passive baselines without drawdown benefit.

Hold, rather than retire, if:

- Data warnings are explainable but require a better source.
- Results are directionally interesting but sample length or trade count is
  insufficient.
- Accounting or sizing issues are engine-level and can be fixed before
  rerunning the same precommitted matrix.

## Sub-Agent Routing

- `strategy-thesis-tracker`: thesis remains `THESIS_UPDATE`.
- `data-audit-reviewer`: next required formal gate.
- `backtest-validator`: blocked until data audit passes and artifacts exist.
- `risk-governor`: blocked until a validated backtest package exists.
- `paper-live-gatekeeper`: not applicable; paper/live-adjacent work is blocked.

## Risk Authorization Needed

No risk authorization is needed for this research-only taskbook.

Human authorization would be required before adding paper configuration,
connecting exchange credentials, modifying capital/risk boundaries, or doing
any live-adjacent work.

## Not Allowed

- No investment advice.
- No investment recommendation.
- No trading permission.
- No paper approval.
- No exchange or broker connection.
- No real credentials, real orders, QMT, live, or real-money claims.
