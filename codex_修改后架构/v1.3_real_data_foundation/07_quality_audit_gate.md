# 07 · Quality 与 Data Audit Gate

## 1. 分层

质量门禁分两层:

1. Deterministic quality checks: 脚本可重复判断结构、主键、时间、数值和完整性。
2. Data audit review: 基于报告判断 dataset 是否可用于指定 research/backtest 目的。

Deterministic checks 不能替代 audit verdict。Audit verdict 不能忽略 hard-fail 证据。

## 2. Verdict

Data audit 输出:

```text
PASS
PASS_WITH_WARNINGS
FAIL
```

`PASS_WITH_WARNINGS` 仅表示 warning 被记录且不破坏 intended use。它不表示 paper/live 通过。

## 3. Common checks

所有 `curated_candidate` 和 `research_ready` dataset 必须检查:

- provider is named。
- build command is known。
- universe is explicit。
- date range is explicit。
- timezone is explicit。
- no duplicate primary keys。
- required OHLCV columns exist。
- OHLC is non-negative and internally plausible。
- volume and amount are non-negative。
- no rows beyond declared decision timestamp。
- latest expected session or interval is present, or dataset is explicitly blocked。
- manual repairs are recorded。
- data hash and manifest hash exist。

## 4. A 股/ETF checks

- bars align with A 股 trade calendar。
- non-trading days are absent unless explicitly marked。
- adjustment factors exist for adjusted-price research。
- instrument exchange suffixes are stable。
- ST, suspension, delisting fields are available or marked unavailable。
- price-limit data is available, computed with documented rule, or marked unavailable。
- raw and adjusted price semantics are not mixed silently。
- latest expected exchange session is present after configured provider update window。

## 5. Crypto checks

- 4h and 1d interval boundaries are complete。
- open time and close time semantics are deterministic。
- cross-source close differences are reported。
- quote currency is explicit。
- symbol trading status is recorded where available。
- 7x24 calendar does not reuse A 股 holiday logic。
- no incomplete current bar is exposed as closed。

## 6. Hard-fail conditions

Hard fail:

- unknown data source。
- missing trade calendar for A 股/ETF daily dataset。
- missing or unexplained adjustment factors for adjusted-price research。
- duplicate primary keys。
- future rows relative to declared decision/simulation time。
- quality issues without report。
- stale latest session without explicit blocked state。
- manual repair without audit note。
- provider field group required by intended use is unavailable。
- provider schema changed and normalization was not reviewed。

Hard fail means lifecycle must be `blocked` or remain below `research_ready`。

## 7. Quality result schema

Machine-readable quality result:

```yaml
schema_version: "1.3"
dataset_id: string
run_id: string
generated_at: timestamp
verdict: PASS | PASS_WITH_WARNINGS | FAIL
lifecycle_state_recommended: curated_candidate | research_ready | blocked
checks:
  - name: string
    status: PASS | WARN | FAIL | SKIP
    severity: INFO | WARN | CRIT
    message: string
    evidence: {}
blocking_issues: []
warnings: []
required_fixes: []
```

`SKIP` 只有在 manifest 记录 field unavailable 且 intended use 不依赖该字段时允许。

## 8. Human-readable report

Quality report 至少包括:

- dataset reviewed。
- intended use。
- provider and coverage。
- lifecycle state before audit。
- blocking issues。
- warnings。
- checks performed。
- evidence。
- required fixes。
- recommended lifecycle state。

## 9. Publication gate

Publication gate 规则:

| 条件 | 结果 |
| --- | --- |
| quality `FAIL` | `blocked` |
| quality `PASS_WITH_WARNINGS` but no audit | `curated_candidate` |
| quality `PASS` but no audit | `curated_candidate` |
| audit `PASS` | `research_ready` |
| audit accepted `PASS_WITH_WARNINGS` | `research_ready` only for documented intended use |
| audit `FAIL` | `blocked` |

Backtest 和 research report 必须引用 dataset id 和 quality/audit artifact,不能只引用 data path。

