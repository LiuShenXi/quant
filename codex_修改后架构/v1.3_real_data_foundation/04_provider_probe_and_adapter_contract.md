# 04 · Provider Probe 与 Adapter 合同

## 1. 目标

Provider 层的职责是发现、抓取、归一化 provider 数据。它不做策略判断,不负责发布 `research_ready`,也不能绕过 staged validation。

Phase 1 的核心不是接更多 provider,而是让每个 provider 的能力、限制、字段权限和失败模式可审计。

## 2. Provider probe

Provider probe 是 adapter 实现前置步骤。它产出 field-availability matrix,用于决定哪些 dataset 可以进入 ingestion。

Probe 必须检查:

- connectivity。
- credential presence,但不能输出 token。
- permission and quota。
- field availability。
- endpoint/function existence。
- sample date range。
- observed columns。
- row count。
- failure reason。
- provider/client version。

## 3. Field-availability matrix

字段矩阵最小列:

| Column | 含义 |
| --- | --- |
| provider | `tushare`, `akshare`, `baostock`, `binance`, `okx`, `coinbase`, `kraken` |
| endpoint_or_function | API endpoint 或 Python function |
| field_group | instruments/calendar/bars/adjust_factors/price_limits 等 |
| permission_result | available/unavailable/partial/error/unknown |
| observed_columns | 实际返回字段 |
| sample_start | probe 样本开始 |
| sample_end | probe 样本结束 |
| row_count | 返回行数 |
| failure_reason | 不可用原因 |
| provider_version | client 或 API version |
| probed_at | probe 时间 |

任何 `unknown` 或 `error` 不得被解释为可用。

## 4. Adapter 能力接口

每个 provider adapter 在适用范围内暴露:

```text
probe_connection()
probe_permissions()
probe_field_availability()
list_instruments()
fetch_history(dataset, symbols, start, end, frequency)
fetch_incremental(dataset, symbols, since)
normalize(raw_path)
write_provider_metadata()
```

接口返回值应是结构化结果,包含 status、metadata、paths、row counts 和 errors。异常可以用于不可恢复错误,但业务失败必须能写入 report。

## 5. Adapter 禁止事项

Provider adapter 不得:

- make strategy decisions。
- 直接写 curated `research_ready`。
- 直接被 `strategies/` import。
- 日志输出 token、账号或 secret。
- 隐藏 partial failure。
- 把缺失字段填成默认值后不写 limitation。
- 在同一次输出里混合不同 provider 语义而不记录来源。

## 6. Phase 1A provider

Primary provider: Tushare Pro configured account。

Cross-check provider: AKShare、BaoStock。

Tushare 权限不得从 “basic permissions” 之类描述推断。Phase 1A 必须 probe:

- instruments and trade calendar。
- A 股/ETF daily bars。
- ETF/fund adjustment factors。
- price limits。
- suspensions。
- ST status。
- daily basic/fundamental fields。

字段不可用时,manifest 必须记录 `missing_fields` 和 `known_limitations`;依赖该字段的 research use case 必须 `blocked` 或保留 `curated_candidate`。

## 7. Phase 1B provider

Primary/sanity provider:

- Binance public market data。
- OKX public market data。
- Coinbase public/advanced market data where accessible。
- Kraken public market data where accessible。

Crypto provider probe 必须检查:

- symbol status。
- interval support for 4h and 1d。
- OHLCV fields。
- quote volume。
- trade count。
- open time and close time semantics。
- rate limit。
- max history window。
- timezone/UTC semantics。

## 8. Partial failure policy

| Failure | 默认动作 |
| --- | --- |
| provider unavailable | keep previous curated snapshot, mark update failed |
| permission denied | mark field unavailable, block dependent dataset |
| schema changed | block normalization and require review |
| partial symbol fetch | block new snapshot unless non-critical by config |
| cross-source divergence | warn or block by threshold severity |
| stale latest session | block affected dataset use |

Adapter 失败不应删除旧 curated snapshot。失败信息必须进入 audit 或 incident artifact。

## 9. Provider onboarding checklist

1. 增加 safe example config。
2. 增加 provider probe command。
3. 运行 field matrix probe。
4. 写 provider metadata schema。
5. 写 raw capture。
6. 写 normalize staged schema。
7. 写 quality negative tests。
8. 写 docs/runbook。
9. 用 small universe 完成 dry-run。
10. Data audit 后才能标记 research-ready。

