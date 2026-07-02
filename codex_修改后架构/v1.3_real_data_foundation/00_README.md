# v1.3 Real Data Foundation 架构包

版本: v1.3 ｜ 定位: 服务策略引擎的数据中台底座 ｜ 状态: 架构包

本架构包把 `2026-07-02-v1.3-real-data-foundation-requirements.md` 落成可执行的技术蓝图。它覆盖完整数据平台方向,但实施必须分期:Phase 1A 先做 data lake、manifest/calendar、provider probe、A 股/ETF 最小闭环;Phase 1B 在 Phase 1A 合同稳定后复用同一套合同加入 crypto;Phase 2/3 只作为后续路线。

本包不是投资建议、交易许可、M4/QMT 批准、券商接入计划或真钱授权。

## 文档地图

| 编号 | 文件 | 内容 |
| --- | --- | --- |
| 01 | `01_cto_architecture_decision.md` | CTO 决策、边界、分期和默认安全动作 |
| 02 | `02_data_lake_architecture.md` | raw/staged/curated/audit 四层数据湖结构 |
| 03 | `03_manifest_lifecycle_contract.md` | dataset manifest、生命周期状态、日历与决策时间合同 |
| 04 | `04_provider_probe_and_adapter_contract.md` | provider probe、字段矩阵、adapter 能力边界 |
| 05 | `05_a_share_etf_phase_1a_architecture.md` | A 股/ETF Phase 1A 闭环架构 |
| 06 | `06_crypto_phase_1b_architecture.md` | Crypto Phase 1B 闭环架构 |
| 07 | `07_quality_audit_gate.md` | 质量检查、data audit verdict、阻塞规则 |
| 08 | `08_daily_update_and_incident_flow.md` | 日更流程、失败分类、恢复路径 |
| 09 | `09_security_and_local_data_isolation.md` | 本地数据、密钥、gitignore、日志脱敏 |
| 10 | `10_integration_with_research_backtest.md` | 与 research/backtest/strategy contract 的集成 |
| 11 | `11_testing_and_acceptance.md` | 测试矩阵、验收标准、不可跳过检查 |
| 12 | `12_phase_2_3_roadmap.md` | 高频数据和机构级数据源路线图 |

## 核心原则

1. 数据先有来源、合同、哈希、质量报告和 audit verdict, 再进入研究。
2. Provider 字段能力必须由 probe 证明,不能靠记忆、文档印象或账号名推断。
3. 策略只消费 `quant.data` 发布的 curated 合同,不得 import provider adapter。
4. 所有新 provider 输出默认是 `fetched`、`staged` 或 `curated_candidate`。
5. `research_ready` 只能来自 data audit 的 `PASS` 或被接受的 `PASS_WITH_WARNINGS`。
6. `paper_candidate` 不是数据层自动晋级状态,必须叠加策略 thesis、data audit、backtest、risk 和人工决策。
7. Phase 1A 不能为了追求全市场覆盖而牺牲最小闭环可审计性。
8. Phase 1B 不能 fork 出 crypto 专用数据合同。
9. Phase 2/3 是路线图,不是当前实现范围。
10. 本包不包含 QMT、broker、实盘网关、真钱交易或真钱授权。

## 推荐阅读顺序

先读 `01`、`03`、`07` 建立边界和门禁,再按实施顺序读 `02`、`04`、`05`。Crypto 实现前读 `06`;日更和运维前读 `08`、`09`;接回测研究前读 `10`、`11`;讨论未来数据采购或分钟级数据前读 `12`。

## 实施顺序

```text
Phase 1A:
gitignore/data isolation
-> manifest/calendar v1.3
-> provider probe matrix
-> A-share/ETF raw/staged/curated/audit closed loop
-> data audit marks research_ready

Phase 1B:
reuse Phase 1A contracts
-> crypto provider probes
-> 4h/1d ingestion
-> venue/timestamp/cross-source checks
-> data audit marks research_ready

Phase 2/3:
enter only after Phase 1 is stable and new evidence justifies the added complexity
```

