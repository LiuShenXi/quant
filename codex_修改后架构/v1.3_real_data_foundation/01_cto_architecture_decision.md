# 01 · CTO 架构决策

## 1. 决策

Decision: `START_FULL_V1_3_ARCHITECTURE_PACKAGE_WITH_PHASED_IMPLEMENTATION`

v1.3 的目标是建立服务策略引擎的数据中台底座,不是下载更多数据源。成功标准是:

```text
Every research dataset has a source, manifest, hash, quality report, audit verdict, update path, and failure mode.
```

本次架构包允许写全 Phase 1A、Phase 1B、Phase 2、Phase 3,但实施必须保持分期:

- Phase 1A: data lake + manifest/calendar + provider probe + A 股/ETF 最小闭环。
- Phase 1B: 复用 Phase 1A 合同加入 crypto provider 闭环。
- Phase 2: 在 Phase 1 稳定后评估分钟和更高频数据。
- Phase 3: 作为数据采购和治理升级,不是简单 adapter 任务。

## 2. 当前边界

本包只覆盖 data foundation。它不包含:

- QMT 或券商接入。
- broker gateway 或 exchange order API。
- 真实账号、真实 token、实盘 overlay。
- 真实资金交易。
- Web 管理界面。
- A 股分钟、tick、Level-2、order-book 历史的当前实现。
- 机构付费源的当前采购或接入。

任何 M4/QMT/live-adjacent 工作仍受 M3b 门禁阻塞。通过数据底座不等于通过策略晋级,也不等于允许 paper/live。

## 3. 架构取舍

| 议题 | 决策 | 理由 |
| --- | --- | --- |
| 仓库位置 | 保留在当前 `quant` modular monolith 内 | 数据合同要直接服务 backtest/research,单人维护优先 |
| 存储形态 | 本地 data lake + Parquet + YAML/JSON manifest + DuckDB 查询 | 无外部服务依赖,可复现,易备份 |
| Provider 设计 | provider adapter 独立于 `quant.data` 读合同 | 策略和回测不能感知 provider 细节 |
| 生命周期 | 显式 `fetched/staged/curated_candidate/research_ready/paper_candidate/blocked` | 阻止未经 audit 的数据被误用 |
| 质量门禁 | 机器质量检查 + human-readable audit report | 确定性检查和人工判断分层 |
| 分期 | Phase 1A 先于 Phase 1B | A 股日历、复权、字段权限复杂,先锁合同 |

## 4. 风险登记

| 风险 | 影响 | 架构控制 |
| --- | --- | --- |
| Provider 权限不足 | 字段缺失但被当作可用 | provider probe matrix 是 Phase 1A 前置产物 |
| A 股日历错误 | 缺 bar 或未来函数 | manifest/calendar 先于 ingestion,质量检查按 session 对齐 |
| 复权口径混用 | 趋势/因子研究结论漂移 | raw 与 adjusted 合同分离,manifest 记录 adjustment policy |
| Crypto 时间戳误解 | 使用未闭合 bar 或错位 bar | manifest 明确 open time、close time、decision timestamp |
| 质量失败仍发布 | 脏数据进入研究或回测 | publication gate 只允许合格 snapshot 标记 `research_ready` |
| 密钥或本地数据入库 | 凭证泄露或仓库污染 | `.gitignore` 与脱敏日志作为 Phase 1A 第一项 |

## 5. 默认安全动作

- 证据缺失: dataset 保持 `curated_candidate` 或 `blocked`。
- Provider probe 失败: 不实现依赖该字段的 research-ready 数据集。
- 质量检查失败: 不发布新 curated snapshot,保留旧 snapshot 并记录 incident。
- audit report 缺失: 不允许 `research_ready`。
- 字段权限不明: 写入 `missing_fields` 或 `known_limitations`,不能静默省略。
- 策略想使用新数据: 必须引用 dataset id、manifest、quality verdict 和 audit artifact。

## 6. CTO 准入结论

本架构包允许启动 Phase 1A 设计和实施计划。准入条件是:

1. Phase 1 仍为 research-only。
2. Phase 1A 不跳过 provider probe。
3. DataService/manifest/calendar 先于 provider ingestion 稳定。
4. 本地 data lake 和 provider secrets 先被 gitignore 或等价 guard 保护。
5. 任何 backtest claim 都必须能引用 data audit artifact。

