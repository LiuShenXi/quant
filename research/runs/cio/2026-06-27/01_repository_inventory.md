# Repository Inventory - 2026-06-27

Status:

`RESEARCH_ONLY_INVENTORY`

Evidence reviewed:

- Governance: `AGENTS.md`, `docs/agents/quant-agent-operating-model.md`, `docs/agents/workflow-strategy-promotion.md`, `docs/agents/risk-authorization-hooks.md`, `docs/agents/quant-cio-agent.md`.
- Architecture: modular monolith under `src/quant/{core,data,backtest,risk,live}`.
- Strategy code: `strategies/dual_ma.py`; research-only external strategy in `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation.py`.
- Strategy config: `config/strategies/dual_ma_510300*.yaml`; research-only ETF rotation YAML in `量化使用记录2026-06-26/strategy_lab/`.
- Data: `data_sample/*.csv`; AKShare ETF datasets under `量化使用记录2026-06-26/data/`.
- Backtest artifacts: `量化使用记录2026-06-26/backtest/*/{orders.csv,trades.csv,equity.csv,events.jsonl,report.md,config_snapshot.yaml}`.
- Paper evidence: `首轮量化使用记录/原始记录/observations/*`, paper ledger, disconnect drill notes.
- Tests: strategy boundary, data, backtest, risk, paper, OMS, alerts, reconciliation, M3b signoff, agent skill tests.

Facts observed:

- The repo intentionally excludes real broker gateways, real-money trading, minute bars, and web UI.
- Current phase supports daily-bar backtest and paper-only infrastructure.
- M4 remains blocked until M3b gate is complete.
- `pyproject.toml` defines import-linter contracts for core/risk boundaries.
- `tests/test_import_boundaries.py` includes a strategy import checker limiting strategy imports to `quant.core.contract`, stdlib, `numpy`, and `pandas`.
- `config/risk/global.yaml` defines independent risk limits, including price collar, order value, position value, gross exposure, order rate, cancel ratio, kill switch, and market-data staleness.
- `config/costs/cn_etf.yaml` includes commission and slippage assumptions: commission rate `0.00025`, minimum `5.0`, slippage `5 bps`.

Deterministic checks performed:

- `rg --files` to inventory repository artifacts.
- `git status --short` to identify pre-existing untracked work.
- `rg "import quant\.(data|backtest|live|risk|ops)|from quant\.(data|backtest|live|risk|ops)"` across strategy directories: no matches found.
- `rg "datetime\.now|date\.today|now\(\)|utcnow|time\."` across strategy directories: no matches found.
- CSV artifact inspection for ETF rotation dataset and backtest artifact row counts.

Important evidence gaps:

- No operator-authored `m3b_signoff.yaml` was found.
- Existing M3b readiness notes show only `1 / 10` counted observation days.
- CRIT phone-side delivery confirmation is missing in the current paper ledger.
- ETF rotation has backtest artifacts but has not yet been through formal `strategy-thesis-tracker -> data-audit-reviewer -> backtest-validator -> risk-governor`.
- Existing ETF rotation data covers a short window, roughly 2025-06 to 2026-06, which is not enough to infer regime robustness.

Git/worktree note:

`git status --short` shows pre-existing untracked governance/agent files including `.agents/`, `AGENTS.md`, `docs/agents/`, `tests/fixtures/`, `tests/test_quant_agent_skills.py`, and `tests/test_quant_cio_skill.py`. This CIO run only adds files under `research/cio-runs/2026-06-27/`.

