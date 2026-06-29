# Candidate Strategy Roadmap - 2026-06-27

Status:

`EXPLORE -> BUILD_THESIS`

Selection principle:

优先选择低复杂度、可审计、已有数据和 artifact、不会触碰 live/QMT/真钱边界的 research-only 候选。回测收益只作为继续研究的线索，不作为 paper 或 live 准入证据。

Candidate strategies:

1. ETF regime rotation v1: `510300.SH` / `510500.SH`
   - Stage: idea with existing research code and backtest artifacts; not yet formal thesis-reviewed.
   - Signal: trend filter plus relative momentum ranking.
   - Evidence present: strategy_lab code/YAML, AKShare ETF dataset, backtest artifacts, iteration note.
   - Key concerns: short history, small universe, benchmark underperformance versus simple `510500` buy-and-hold in the inspected period, no formal data/backtest/risk reviews.
   - CIO action: select for first `strategy-thesis-tracker` record.

2. DualMA 510300 paper validation baseline
   - Stage: existing strategy already used for paper infrastructure validation.
   - Signal: moving-average crossover.
   - Evidence present: strategy code, configs, backtest artifacts, paper run evidence, M3b readiness notes.
   - Key concerns: current role is mostly system validation, not a strong alpha thesis; M3b only has `1 / 10` counted days.
   - CIO action: hold as operational baseline; continue paper evidence collection only inside existing gate.

3. DualMA 510500 variant
   - Stage: backtest artifact exists.
   - Signal: moving-average crossover on `510500.SH`.
   - Evidence present: dataset and backtest output.
   - Key concerns: weaker thesis than rotation; drawdown sensitivity needs review; no formal thesis.
   - CIO action: keep in candidate pool, behind ETF rotation.

4. ETF risk-off cash filter
   - Stage: research idea.
   - Signal: stay in cash when all candidates fail a trend or drawdown filter.
   - Evidence present: current ETF rotation already contains a trend filter and can hold no candidate.
   - Key concerns: easy to overfit with short sample; needs longer data before parameter experiments.
   - CIO action: defer until selected rotation thesis passes data audit.

5. Broader liquid ETF momentum basket
   - Stage: research idea.
   - Signal: extend universe beyond `510300.SH` and `510500.SH`.
   - Evidence present: none in current repository beyond current ETF data builder capability.
   - Key concerns: data scope, survivorship, liquidity, capacity, and instrument list governance.
   - CIO action: hold until data-audit process for multi-ETF universe is defined.

Recommended first candidate:

`ETF regime rotation v1` should enter thesis stage first because it has the best combination of existing artifacts, simple rules, daily frequency, inspectable code, and clear falsifiers. It remains research-only.

Next routing:

```text
strategy-thesis-tracker
-> data-audit-reviewer
-> backtest-validator
-> risk-governor
-> paper observation only if prior gates pass
```

