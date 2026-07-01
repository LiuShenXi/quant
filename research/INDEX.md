# 研究索引

本文件是当前量化研究的人工可读索引。

## 活跃研究

| 研究包 | 主题 | 状态 | 下一次审查 |
| --- | --- | --- | --- |
| `runs/2026-07-01T1703__crypto_trend_breadth_top2_admission` | Crypto trend breadth top2 admission | `CONTINUE_RESEARCH_ONLY_ADMISSION` | 选择并构建可审计 4h crypto 数据集；通用引擎 framework gate 通过前不得做正式回测结论 |
| `runs/2026-07-01__post_etf_v1_research_queue` | ETF v1 退休后的研究队列 | `SET_POST_ETF_V1_RESEARCH_QUEUE` | 下一主线优先做 `crypto_trend_breadth_top2_v1` 准入审查，仅限 thesis/data/framework gate |
| `runs/2026-07-01__etf_rotation_long_history_robustness` | ETF 轮动长历史鲁棒性 | `RETIRE_ETF_ROTATION_V1_FAMILY` | v1 家族已退休；仅保留研究素材、引擎修复证据和未来 ETF 仓位管理反例约束 |
| `runs/2026-06-29__etf_rotation_evidence_normalization` | ETF rotation evidence normalization | `HOLD_FOR_ROBUSTNESS` | Execute robustness experiment package |
| `runs/cio/2026-06-27` | ETF regime rotation CIO package | imported existing run | Needs registry normalization |

## 导入记录

| 路径 | 来源 | 状态 |
| --- | --- | --- |
| `imported/usage_records/2026-06-26__quant_usage_record` | 早期量化使用记录 | 历史素材，不是正式研究包 |

## 运行规则

新的非平凡研究任务优先使用 `runs/YYYY-MM-DDTHHMM__topic/`，并且在任何
晋级讨论前更新 `registries/`。所有研究输出都不是投资建议、交易许可或
paper/live 准入。
