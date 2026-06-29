# Evidence Inventory

Cross-run index of evidence packages and artifacts.

| Evidence ID | Path | Type | Related strategy | Review status |
| --- | --- | --- | --- | --- |
| `longer_history_data_probe_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/12_longer_history_data_probe.md` | `data_audit` | `etf_regime_rotation_v1` | `FAIL`; data dependency blocked |
| `sample_split_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/11_sample_split_report_enablement.md` | `backtest_review` | `etf_regime_rotation_v1` | Current-window sample split generated |
| `benchmark_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/10_benchmark_report_enablement.md` | `backtest_review` | `etf_regime_rotation_v1` | Current-window benchmark report generated |
| `repo_report_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/09_repo_report_generator_enablement.md` | `backtest_review` | `etf_regime_rotation_v1`, DualMA baseline | Core metrics reports generated |
| `repo_inspector_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization/08_repo_inspector_enablement.md` | `backtest_review` | `etf_regime_rotation_v1`, DualMA baseline | Artifact completeness checks passed |
| `etf_rotation_normalization_2026_06_29` | `runs/2026-06-29__etf_rotation_evidence_normalization` | `cio_package`, `thesis`, `data_audit`, `backtest_review`, `risk_review` | `etf_regime_rotation_v1` | `HOLD_FOR_ROBUSTNESS` |
| `usage_2026_06_26` | `imported/usage_records/2026-06-26__quant_usage_record` | Historical usage record | ETF rotation and dual MA experiments | Source material for evidence extraction |
| `cio_2026_06_27` | `runs/cio/2026-06-27` | CIO package | `etf_regime_rotation_v1` | Existing package |

## Evidence Types

- `thesis`
- `data_audit`
- `backtest_artifact`
- `backtest_review`
- `risk_review`
- `paper_observation`
- `gate_signoff`
- `cio_package`
- `legacy_import`
