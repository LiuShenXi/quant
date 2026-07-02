# 08 · Daily Update 与 Incident Flow

## 1. 目标

Daily update 负责把新 provider 数据转为新的 curated candidate。它不是策略调度器,不触发交易,也不绕过 audit gate。

目标:

- 可定时运行。
- 可 dry-run。
- 可重复运行。
- 失败时保留旧可用 snapshot。
- 所有失败有分类、日志、报告和恢复路径。

## 2. 标准流程

```text
load config
-> verify data_lake and secret isolation guard
-> verify provider credentials/connectivity
-> load or refresh provider field matrix
-> fetch raw increment
-> write raw metadata and hashes
-> normalize staged data
-> merge/build curated_candidate snapshot
-> run quality checks
-> write manifest/hash/quality report
-> publish only if gates pass
-> mark blocked if gates fail
```

Phase 1A 只需要 A 股/ETF daily update。Phase 1B 才加入 crypto 4h/1d update。

## 3. Schedule

A 股/ETF:

- 建议窗口: `17:30-20:30 Asia/Shanghai`。
- 不能假设收盘后 provider 立即可用。
- latest expected session 必须由 calendar 和 provider update window 共同决定。

Crypto:

- 4h: 每个 UTC 4h close 后加 confirmation delay。
- 1d: UTC daily close 后加 confirmation delay。
- 不得把当前未闭合 bar 当作 closed bar。

Schedule 必须配置化。策略不能假设新数据已经可用,只能相信 quality report。

## 4. Failure categories

| Category | 含义 | 默认动作 |
| --- | --- | --- |
| `provider_unavailable` | source API failed or timed out | keep previous curated snapshot; mark update failed |
| `partial_fetch` | some symbols/frequencies missing | block new snapshot unless configured non-critical |
| `schema_changed` | provider columns changed unexpectedly | block and require review |
| `quality_failed` | deterministic checks failed | block and write report |
| `cross_source_divergence` | sources disagree beyond threshold | block or warn by severity |
| `stale_data` | expected latest session missing | block affected dataset |
| `manual_repair_required` | automated repair is unsafe | block until documented review |
| `secret_missing` | required credential absent | stop before provider call |
| `secret_leak_detected` | token-like value found in output/log | stop, quarantine artifact, require review |

任何 failure 都不能静默发布新的 `research_ready`。

## 5. Idempotency

Daily update 必须支持重复运行:

- 同一 raw payload 的 hash 不变。
- 同一 staged normalize 结果 hash 不变。
- 同一 curated snapshot 输入不变时 hash 不变。
- 重跑失败不能破坏上一个可用 snapshot。
- append-only raw 层允许多次 run,但 run id 必须区分。

## 6. Publish policy

推荐使用 pointer 文件或 registry 表指向 latest usable snapshot:

```text
dataset_registry.yaml
  dataset_id:
    latest_curated_candidate: path
    latest_research_ready: path
    latest_blocked: path
```

质量失败时只更新 failed/block artifact,不更新 `latest_research_ready`。

## 7. Incident record

Incident report 至少包含:

- incident id。
- dataset id。
- run id。
- category。
- started_at / detected_at。
- provider。
- affected symbols/frequencies。
- lifecycle state before and after。
- old snapshot retained。
- blocking issue。
- recovery action。
- operator note if manual repair。

## 8. Recovery

Recovery 默认路径:

1. 保留旧 `research_ready` snapshot。
2. 修复 provider/config/schema 问题。
3. 重新运行 dry-run。
4. 对比 hashes and row counts。
5. 重跑 quality checks。
6. 需要人工解释时写 audit note。
7. 通过 data audit 后再更新 published pointer。

## 9. 与风险 hooks 的关系

Market-data hook 要求 stale/missing data 不能继续作为可执行依据。v1.3 虽然是 research-only,但必须为未来 hooks 留出 artifact:

- stale data report。
- blocked dataset state。
- latest expected session evidence。
- quality verdict。

这些 artifact 将来可被 paper/live monitor 读取,但 Phase 1 不实现真钱交易。

