# 02 · Data Lake 架构

## 1. 目标

Data lake 的目标是把 provider 输出变成可审计、可复现、可阻塞的研究数据资产。它不是策略特征库,也不是实时交易数据通道。

核心流:

```text
raw provider output
-> staged normalized schema
-> curated snapshot candidate
-> quality and audit artifacts
-> research_ready publication only after gate
```

## 2. 推荐目录

```text
data_lake/
  raw/
    provider=<provider>/
      dataset=<dataset>/
        ingest_date=YYYY-MM-DD/
          request.json
          payload.*
          metadata.yaml
          hashes.yaml
  staged/
    asset_class=<asset_class>/
      dataset=<dataset>/
        run_id=<run_id>/
          *.parquet
          normalize_report.yaml
  curated/
    dataset_id=<dataset_id>/
      version=<as_of_or_run_id>/
        dataset_manifest.yaml
        data/
          *.parquet
        hashes.yaml
        quality_result.yaml
        quality_report.md
  audit/
    dataset_id=<dataset_id>/
      version=<as_of_or_run_id>/
        data_audit.md
        data_audit.yaml
        field_availability_matrix.csv
        cross_source_report.csv
```

路径命名可以在实施时微调,但四层职责不能合并。

## 3. Raw 层

Raw 层保存 provider 返回值和请求上下文,用于复现和故障分析。

必须记录:

- provider 名称。
- endpoint 或 API function。
- request params,但不能包含 token。
- provider response status。
- ingest timestamp。
- provider package version 或 API version。
- source timezone。
- row count。
- content hash。
- source license note。

规则:

- Raw 文件 append-only。
- 不允许静默覆盖同一路径的 raw payload。
- Raw payload 不得包含 API key、auth token、账号 ID 或真实交易账户信息。
- Raw 文件不能被策略、backtest 或 research report 直接消费。

## 4. Staged 层

Staged 层把 provider 字段转换为平台 typed schema。它是结构校验区,不是研究发布区。

要求:

- 每种 dataset type 有稳定 schema。
- 主键显式,例如 `(symbol, dt, frequency)` 或 crypto 的 `(venue, symbol, open_time, frequency)`。
- 时间戳带 timezone 或明确的 UTC 规范。
- 保留 source/provider 字段。
- 不写策略特征,不做策略过滤。
- 任何 forward fill、缺失填充、单位转换必须写入 normalize report。

Staged 层允许失败。失败结果应产出 report,不得被包装成 curated。

## 5. Curated 层

Curated 层是 research/backtest 可引用的 snapshot 位置,但默认只是 `curated_candidate`。

必须包含:

- `dataset_manifest.yaml`。
- Parquet 数据文件。
- `hashes.yaml`。
- `quality_result.yaml`。
- `quality_report.md`。
- universe definition。
- calendar policy。
- adjustment policy。
- provider metadata。
- known limitations and missing fields。

Curated snapshot 采用不可变版本目录。若同一 as-of 重新构建,必须产生新的 run/version 或相同输入下 hash 完全一致。

## 6. Audit 层

Audit 层解释数据能否被信任。它连接确定性质量检查和人工审查。

产物:

- machine-readable audit verdict。
- human-readable audit report。
- blocking issues。
- warnings。
- checks performed。
- required fixes。
- cross-source comparison。
- provider field matrix。

Audit artifact 是 research/backtest claim 的证据入口。没有 audit artifact 的数据不能成为 `research_ready`。

## 7. DuckDB 使用边界

DuckDB 用于本地查询和验证:

- 读取 Parquet。
- 做 row count、duplicate key、缺失 session、cross-source 差异检查。
- 生成质量报告输入。

DuckDB 不承担必须常驻的数据库服务角色。Phase 1 不要求外部数据库服务器。

## 8. 数据不可变与可复现

每个 curated snapshot 必须能回答:

1. 谁构建的: command、code version、generated_at。
2. 用什么构建的: raw path、provider、request params。
3. 产出是什么: data hash、manifest hash、row count。
4. 能不能用: quality verdict、audit verdict、lifecycle state。
5. 有什么限制: missing fields、known limitations、license note。

## 9. 禁止事项

- 禁止策略直接读取 `data_lake/raw` 或 provider payload。
- 禁止 provider adapter 直接写 `research_ready`。
- 禁止覆盖 raw payload 后只保留新文件。
- 禁止把 provider-specific column 暴露给策略。
- 禁止把本地密钥、真实账号、token 写入 data lake。
- 禁止把 quality failed snapshot 发布成最新可用数据。

