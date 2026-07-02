# 策略登记册

跨研究包维护的长期策略台账。

| 策略 ID | 名称 | 资产范围 | 频率 | 阶段 | 最新研究包 | 负责人 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `a_share_limit_up_continuation_v0` | A-share limit-up continuation v0 | 沪深 A 股个股初筛，排除 ST/停牌/退市风险/新股/特殊规则，待数据审查确认 | Daily first, intraday/order-book required for board capture | `thesis_draft` | `runs/2026-07-02T1114__a_share_limit_up_continuation_v0` | Codex research | `RESEARCH_ONLY_THESIS_DRAFT`；仅限 thesis 和数据需求；不得 paper/live/QMT/真钱 |
| `etf_regime_rotation_v1` | ETF regime rotation v1 | `510300.SH`, `510500.SH` | Daily | `retired` | `runs/2026-07-01__etf_rotation_long_history_robustness` | Codex research | `DEMOTE_TO_RESEARCH_MATERIAL`; family retired; failed paper gate; research-only |
| `etf_regime_rotation_v1b_low_turnover` | ETF regime rotation low-turnover hypothesis | `510300.SH`, `510500.SH` | Daily | `retired` | `runs/2026-07-01__etf_rotation_long_history_robustness` | Codex research | `RETIRE_V1B_MAINLINE`；不得 paper；仅保留研究素材 |
| `crypto_trend_breadth_top2_v1` | Crypto trend breadth top2 design | `BTC`, `ETH`, `SOL`, stablecoin cash | 4h / Daily | `smoke_only` | `runs/2026-07-02T1030__crypto_trend_breadth_smoke_admission` | Codex research | `CRYPTO_RESEARCH_TASKBOOK_LOCKED`；CIO 已冻结主候选、基线、消融和 kill/hold 标准；真实数据/正式回测仍 FAIL；不得 paper/live/交易所/真钱 |

## 阶段词汇

- `idea`
- `thesis_draft`
- `data_review`
- `smoke_only`
- `backtest_review`
- `risk_review`
- `paper_observation`
- `m3b_gate`
- `retired`

本登记册里的任何阶段名称都不代表交易许可。
