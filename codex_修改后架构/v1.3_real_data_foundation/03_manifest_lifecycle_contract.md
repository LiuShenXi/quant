# 03 · Manifest Lifecycle 合同

## 1. Manifest 的职责

Manifest 是 dataset 的证据目录。它不是注释文件,而是研究和回测能否使用数据的机器合同。

Manifest 必须表达:

- dataset identity。
- asset class。
- universe。
- lifecycle state。
- source and license。
- storage paths。
- calendar and timezone。
- decision time policy。
- coverage。
- frequency。
- adjustment policy。
- quality verdict。
- hashes。
- known limitations。
- missing fields。

## 2. 生命周期状态

| State | 含义 | 允许用途 |
| --- | --- | --- |
| `fetched` | Raw provider output 已存在 | Inspection only |
| `staged` | 已归一化到 common schema | Structural tests only |
| `curated_candidate` | 有 manifest、metadata、hash、quality report,但未通过 data audit | Audit review only, no backtest claim |
| `research_ready` | data audit 为 `PASS` 或接受的 `PASS_WITH_WARNINGS` | Research/backtest allowed |
| `paper_candidate` | 策略级 thesis、data、backtest、risk 证据齐备 | Paper review only |
| `blocked` | 缺失、陈旧、不一致或未审计 | No strategy use |

数据层只能自动推进到 `curated_candidate` 或 `blocked`。`research_ready` 必须引用 audit verdict。`paper_candidate` 不是数据层单独决定的状态。

## 3. Manifest 最小 schema

```yaml
schema_version: "1.3"
dataset_id: string
asset_class: a_share | etf | crypto
lifecycle_state: fetched | staged | curated_candidate | research_ready | paper_candidate | blocked
universe_id: string
frequency: 1d | 4h | other
as_of: timestamp
decision_time:
  timestamp: timestamp
  policy: fully_closed_bar | exchange_session_close | provider_publish_time | manual_snapshot
coverage:
  start: timestamp_or_date
  end: timestamp_or_date
timezone: string
calendar:
  name: string
  type: exchange_sessions | continuous_24x7
  source: string
adjustment_policy: raw | qfq | hfq | none | mixed_with_fields
build:
  command: string
  code_version: string
  generated_at: timestamp
source:
  provider_primary: string
  provider_cross_checks: []
  endpoint_or_function: string
  request_params: {}
  provider_version: string_or_null
  retrieved_at: timestamp
license:
  usage_scope: research_only | unknown | contracted
  source_license_note: string
  redistribution_allowed: false
storage:
  raw_path: path
  staged_path: path
  curated_path: path
quality:
  verdict: PASS | PASS_WITH_WARNINGS | FAIL
  report_path: path
  generated_at: timestamp
  lifecycle_state_after_audit: fetched | staged | curated_candidate | research_ready | blocked
hashes:
  manifest_sha256: string
  data_sha256: string_or_map
known_limitations: []
missing_fields: []
```

实施可扩展字段,但不能移除这些概念。

## 4. 日历合同

Phase 1A 必须支持 exchange session calendar,不能把 A 股日线塞进 `continuous_24x7`。

Calendar manifest 应能表达:

- calendar name,例如 `sse_szse_a_share_daily`。
- timezone,例如 `Asia/Shanghai`。
- session dates。
- session close time,例如 `15:00:00`。
- calendar source/provider。
- coverage start/end。
- holidays and non-trading days。
- missing or provisional sessions。

A 股 daily bar 的 `dt` 应表示 session close time。Crypto 4h/1d 的 engine-facing `dt` 应表示 fully closed bar boundary。

## 5. Decision time 合同

Manifest 必须声明 `dt` 和 `decision_time` 的关系:

| Policy | 含义 | 适用 |
| --- | --- | --- |
| `exchange_session_close` | bar 在交易所 session close 后才可见 | A 股/ETF daily |
| `fully_closed_bar` | bar 完全闭合后才可见 | Crypto 4h/1d |
| `provider_publish_time` | 以 provider 发布时间为可用时间 | 可能延迟发布的数据 |
| `manual_snapshot` | 人工固定快照时间 | 研究导入或审查包 |

任何行数据不得晚于 manifest 声明的 decision timestamp,除非明确处于 inspection-only 状态。

## 6. Raw 和 adjusted 口径

数据合同必须区分:

- raw price bars。
- qfq adjusted bars。
- hfq adjusted bars。
- factor table。
- mixed fields。

默认原则仍是:存 raw + factor,查询时按 `end` 动态复权。若 Phase 1 为方便研究落地 adjusted parquet,必须同时保留 raw、factor、adjustment base 和构建 hash。

## 7. 与现有 `DatasetManifest` 的迁移

现有实现已支持基础 manifest、multi-frequency 和 `continuous_24x7`。v1.3 不应破坏旧 fixture。

推荐迁移策略:

1. 保留旧 manifest 读取路径。
2. 新增 v1.3 schema model 或 wrapper。
3. DataService 读取 curated dataset 时同时检查 lifecycle and quality。
4. 对 legacy `data_sample/` 继续兼容,但不得把 legacy 样例自动视为 v1.3 `research_ready`。
5. A 股 exchange calendar 先进入 calendar contract,再接 provider ingestion。

## 8. Manifest 验收

Phase 1A manifest 验收必须覆盖:

- 缺 `schema_version` 拒绝。
- 缺 lifecycle state 拒绝。
- `research_ready` 但缺 audit report 拒绝。
- A 股 daily dataset 缺 exchange calendar 拒绝。
- adjusted research 缺 adjust factors 或 unavailability note 拒绝。
- provider source unknown 拒绝。
- duplicate storage path 或 missing hash 拒绝。

