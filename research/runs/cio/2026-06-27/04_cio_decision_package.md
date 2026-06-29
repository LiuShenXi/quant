# Quant CIO Decision Package - 2026-06-27

CIO Decision:

`HOLD_FOR_ROBUSTNESS`

Strategy opportunity:

ETF regime rotation between `510300.SH` and `510500.SH` is the best first research-only candidate because the repository already contains inspectable code, config, data, and backtest artifacts, while the hypothesis remains simple enough to audit.

Recommended next action:

Build a stronger research evidence package for ETF rotation v1 before any risk or paper discussion: full report, longer history if reproducible, sample split, cost sensitivity, and benchmark comparison.

Candidate strategies:

1. ETF regime rotation v1: selected for thesis.
2. DualMA 510300 paper validation baseline: hold as operational baseline; continue existing M3b evidence collection only.
3. DualMA 510500: keep in candidate pool.
4. ETF risk-off cash filter: defer until data audit passes.
5. Broader liquid ETF momentum basket: hold until multi-ETF data governance exists.

Evidence reviewed:

- Governance docs and repo constitution.
- Strategy code and YAML for `DualMA` and ETF rotation research.
- Risk and cost configs.
- ETF rotation data artifact row counts.
- ETF rotation backtest artifact row counts.
- Paper readiness notes showing M3b is incomplete.
- Import/time boundary greps for strategy code.
- Data audit artifact: `research/cio-runs/2026-06-27/05_data_audit_etf_regime_rotation_v1.md`.
- Backtest validation artifact: `research/cio-runs/2026-06-27/06_backtest_validation_etf_regime_rotation_v1.md`.
- Robustness probe artifact: `research/cio-runs/2026-06-27/07_robustness_probe_etf_regime_rotation_v1.md`.

Experiments run:

- Repository inventory via `rg --files`.
- Worktree check via `git status --short`.
- Strategy boundary grep for forbidden imports.
- Strategy time-source grep for direct system time use.
- CSV row-count inspection for ETF rotation dataset and artifacts.
- Paper readiness evidence review from observation docs and ledger.
- Verification command `python -m pytest tests\test_import_boundaries.py tests\test_quant_cio_skill.py tests\test_quant_agent_skills.py` returned 57 passed and 1 failed. The failure was `test_import_linter_contracts_are_kept`, caused by missing `lint-imports` executable at the Python executable directory on this Windows environment.
- Follow-up verification command `python -m pytest tests\test_import_boundaries.py::test_strategy_imports_only_contract_and_allowed_libraries tests\test_import_boundaries.py::test_strategy_import_checker_rejects_non_allowed_third_party tests\test_quant_cio_skill.py tests\test_quant_agent_skills.py` returned 56 passed.
- Reproduced ETF rotation backtest into `research/cio-runs/2026-06-27/repro_etf_regime_rotation_v1`; reproduced orders, trades, and equity matched original artifacts exactly.
- Ran same-window benchmark probe. ETF rotation returned `20.10%` with `-6.49%` max drawdown; `510300.SH` returned `27.57%` with `-9.94%` max drawdown; `510500.SH` returned `59.30%` with `-14.02%` max drawdown; equal-weight close index returned `46.30%` with `-11.36%` max drawdown.

Sub-agent routing:

```text
Quant CIO Orchestrator: complete first route classification and roadmap
Strategy Research Agent / strategy-thesis-tracker: complete THESIS_DRAFT
Data Audit Agent / data-audit-reviewer: PASS_WITH_WARNINGS for research/backtest through 2026-06-25
Backtest Review Agent / backtest-validator: PASS_WITH_WARNINGS for continuing research; HOLD_FOR_ROBUSTNESS before risk or paper
Risk Governor Agent / risk-governor: blocked until fuller robustness package
Paper/Live Gatekeeper / paper-live-gatekeeper: not applicable to this thesis step; M4 remains blocked by incomplete M3b evidence
```

Improvement proposal:

Keep ETF rotation v1 as a research-only candidate, but narrow the thesis toward drawdown-controlled participation rather than absolute-return alpha unless longer-history tests contradict the current benchmark probe:

- Data: extend and reproduce the ETF dataset; preserve hashes and build logs.
- Backtest: produce full report; compare against `510300`, `510500`, equal-weight, cash-filtered baselines; include cost sensitivity and sample splits.
- Risk: keep gross exposure below configured limits and require independent `quant.risk` checks before paper.
- Process: keep all strategy changes in the promotion workflow instead of ad hoc parameter tuning.

Risk authorization needed:

`Strategy approval hook` is needed only for formal inclusion in the research roadmap. No capital expansion, paper admission, M4, QMT, broker, or live authorization is requested.

Blocking issues:

- ETF rotation has no formal data audit.
- ETF rotation backtest validation is `PASS_WITH_WARNINGS` for research only; it is not sufficient for paper.
- ETF rotation has no formal risk-governor conclusion.
- ETF rotation has no paper observation evidence.
- ETF rotation lacks longer-history, sample-split, cost-sensitivity, and benchmark-robustness evidence.
- Same-window benchmark probe shows ETF rotation underperformed `510300.SH`, `510500.SH`, and equal-weight close-index baselines on absolute return.
- ETF rotation dataset bars stop at `2026-06-25` while the included trade calendar reaches `2026-06-26`; this is acceptable only as a documented research/backtest warning for the inspected artifact window.
- M3b is incomplete: current notes show `1 / 10` counted days, missing CRIT phone-side confirmation, no operator-authored signoff package, and no successful signoff validation output.
- Local verification environment lacks the `lint-imports` command entry expected by `tests/test_import_boundaries.py::test_import_linter_contracts_are_kept`.

Default safe option:

Keep selected strategy in research-only status. Hold paper/live-adjacent progression.

Not allowed:

- No real-money trading.
- No investment advice, investment recommendation, or trading permission.
- No QMT, broker, or real live gateway integration.
- No bypass of `quant.risk`.
- No use or commit of real credentials, account IDs, tokens, or local live overlays.
- No M4 work unless M3b signoff validation produces `M4a may start`, and even that would only allow human-reviewed engineering discussion, not real-money trading.

Next loop:

Run longer-history robustness experiments for ETF rotation v1. If the lower-return/lower-drawdown tradeoff is not compelling, retire or downgrade the candidate and return to the pool. If robustness improves, prepare a risk-governor package without requesting paper admission.
