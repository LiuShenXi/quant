# Quant CIO Target Mode - 2026-06-27

Objective:

在 `C:\WORK-SPACE\quant` 仓库内，从零开始构建一个可审计、可复现、只限 research/paper 阶段的量化策略研发与持续优化闭环。

Operating loop:

```text
Monitor -> Diagnose -> Propose -> Validate -> Promote / Hold / Retire
```

Scope:

- 只允许 research、backtest evidence review 和 paper-only 观察路径。
- 不批准、暗示批准或执行真钱交易。
- 不接入真实券商、QMT 或 live gateway。
- 不绕过 `quant.risk`。
- 不提交真实凭证、账号、token 或本地 live overlay。

Promotion rule:

```text
idea
-> strategy-thesis-tracker
-> data-audit-reviewer
-> backtest-validator
-> risk-governor
-> paper observation
-> paper-live-gatekeeper
-> human decision
```

Default safe option:

证据不足时保持 research-only 或 hold；涉及 M4/QMT/live-adjacent 时，在 M3b 证据不足或签核包未通过前输出 `M4_BLOCKED` 或 `NEEDS_MORE_PAPER`。

Artifacts in this run:

- `01_repository_inventory.md`
- `02_candidate_strategy_roadmap.md`
- `03_thesis_etf_regime_rotation_v1.md`
- `04_cio_decision_package.md`
- `05_data_audit_etf_regime_rotation_v1.md`
- `06_backtest_validation_etf_regime_rotation_v1.md`
- `07_robustness_probe_etf_regime_rotation_v1.md`
- `repro_etf_regime_rotation_v1/`
