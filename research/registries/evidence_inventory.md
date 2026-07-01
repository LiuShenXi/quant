# 证据清单

跨研究包索引，用于追踪证据包和 artifact。

| 证据 ID | 路径 | 类型 | 相关策略 | 审查状态 |
| --- | --- | --- | --- | --- |
| `crypto_top2_admission_2026_07_01T1703` | `runs/2026-07-01T1703__crypto_trend_breadth_top2_admission` | `thesis`, `data_source_screen`, `experiment_design`, `risk_review`, `framework_gap`, `cio_package` | `crypto_trend_breadth_top2_v1` | `CONTINUE_RESEARCH_ONLY_ADMISSION`；无审计数据/正式回测；不得交易 |
| `post_etf_v1_research_queue_2026_07_01` | `runs/2026-07-01__post_etf_v1_research_queue` | `cio_package`, `research_queue`, `admission_gate` | `crypto_trend_breadth_top2_v1`, DualMA baselines, ETF future ideas | `SET_POST_ETF_V1_RESEARCH_QUEUE`；下一步仅做 crypto 准入审查，不得交易 |
| `long_history_robustness_2026_07_01` | `runs/2026-07-01__etf_rotation_long_history_robustness` | `data_audit`, `backtest_review`, `risk_review`, `cio_package`, `execution_gate`, `disposition`, `risk_off_baseline`, `low_turnover_falsification`, `low_turnover_stability`, `regime_failure_review`, `drawdown_control_thesis`, `fixed_exposure_substitution`, `path_smoothing_utility`, `family_final_disposition` | `etf_regime_rotation_v1`, `etf_regime_rotation_v1b_low_turnover` | `RETIRE_ETF_ROTATION_V1_FAMILY`；仅保留研究素材、引擎修复证据和未来约束 |
| `longer_history_data_probe_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/12_longer_history_data_probe.md` | `data_audit` | `etf_regime_rotation_v1` | `FAIL`; data dependency blocked |
| `sample_split_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/11_sample_split_report_enablement.md` | `backtest_review` | `etf_regime_rotation_v1` | Current-window sample split generated |
| `benchmark_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/10_benchmark_report_enablement.md` | `backtest_review` | `etf_regime_rotation_v1` | Current-window benchmark report generated |
| `repo_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/09_repo_report_generator_enablement.md` | `backtest_review` | `etf_regime_rotation_v1`, DualMA baseline | Core metrics reports generated |
| `repo_inspector_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/08_repo_inspector_enablement.md` | `backtest_review` | `etf_regime_rotation_v1`, DualMA baseline | Artifact completeness checks passed |
| `etf_rotation_normalization_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization` | `cio_package`, `thesis`, `data_audit`, `backtest_review`, `risk_review` | `etf_regime_rotation_v1` | `HOLD_FOR_ROBUSTNESS` |
| `usage_2026_06_26` | `imported/usage_records/2026-06-26__quant_usage_record` | Historical usage record | ETF rotation and dual MA experiments | Source material for evidence extraction |
| `cio_2026_06_27` | `runs/cio/2026-06-27` | CIO package | `etf_regime_rotation_v1` | Existing package |

## 证据类型

- `thesis`
- `data_audit`
- `backtest_artifact`
- `backtest_review`
- `risk_review`
- `paper_observation`
- `gate_signoff`
- `cio_package`
- `legacy_import`
