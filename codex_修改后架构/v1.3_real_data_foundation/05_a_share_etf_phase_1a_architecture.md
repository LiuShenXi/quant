# 05 · A 股/ETF Phase 1A 架构

## 1. 范围

Phase 1A 是 v1.3 的第一实施目标:

```text
data isolation
-> manifest/calendar v1.3
-> provider probe matrix
-> A-share/ETF daily ingestion
-> staged validation
-> curated_candidate snapshot
-> quality report
-> data audit
-> research_ready only after verdict
```

Phase 1A 不追求 full-market daily bars。它追求小 universe 的可审计闭环。

## 2. 最小 universe

Metadata-only discovery:

- 全 active A 股 instrument list,如果 provider 权限允许。
- 全 ETF/fund instrument list,如果 provider 权限允许。
- 用于 survivorship 和 identity 检查,不代表 daily bars 全量接入。

First-pass daily bars:

- `510300.SH`
- `510500.SH`
- 可配置 A 股样本,建议 10-20 个 symbol。

Full-market bars 必须等最小闭环通过 data audit 后再讨论。

## 3. 必需 dataset

| Dataset | 必需字段 | 用途 |
| --- | --- | --- |
| `instruments` | symbol, exchange, name, asset type, listing date, delisting date, status | identity and survivorship |
| `trade_calendar` | date, exchange, open/closed status | session alignment |
| `bars_1d_raw` | symbol, session dt, open, high, low, close, volume, amount | raw-price research and execution assumptions |
| `adjust_factors` | symbol, date, factor, factor type/source | adjusted research |
| `bars_1d_adjusted` | symbol, dt, adjusted OHLC when available or reproducible | trend/factor research |
| `suspensions` | symbol, date, suspension/resumption state | tradability checks |
| `st_status` | symbol, date or interval, ST flag | universe filters |
| `price_limits` | symbol, date, limit_up, limit_down | limit-up/down research and matching |
| `daily_basic` | turnover, float market cap, total market cap, PE/PB if available | liquidity/factor screens |

字段不可用时,不得静默省略。Manifest 必须记录 missing field 和影响范围。

## 4. A 股日历

Phase 1A 必须先扩展或包装现有 calendar contract。

要求:

- 支持 exchange session calendar。
- `Bar.dt` 表示 session close,默认 `15:00:00 Asia/Shanghai`。
- `trade_calendar` 中 open session 必须与 bars 对齐。
- 非交易日 bar 默认是 hard fail,除非 manifest 明确说明特殊 session。
- missing latest session 应导致 `blocked` 或 quality `FAIL`,不能 silently publish。

## 5. 复权与 raw price

默认存储:

- raw OHLCV。
- adjust factors。
- adjustment policy。

动态前复权仍以 request end 或回测当前时刻为基准,不能用最新日期。若构建 adjusted parquet,必须记录:

- factor source。
- factor date。
- adjustment base。
- raw data hash。
- adjusted output hash。

Adjusted-price research 缺 adjust factors 或解释时必须 hard fail。

## 6. Provider 方向

Tushare Pro 是 primary candidate,但字段权限必须 probe。

AKShare 和 BaoStock 用于 cross-check:

- close。
- volume。
- representative sample。
- date alignment。

Cross-check 差异超过阈值时:

- 轻微差异: `PASS_WITH_WARNINGS`,写明影响。
- 影响结论差异: `FAIL` 或 `blocked`。

## 7. Pipeline

```text
load Phase 1A config
-> verify gitignored paths and safe secret config
-> run provider probe if matrix missing or expired
-> fetch raw increments
-> write raw metadata and hashes
-> normalize staged tables
-> validate staged schema and primary keys
-> build curated_candidate snapshot
-> run quality checks
-> write manifest/hash/quality report
-> request/record data audit verdict
-> mark research_ready only when allowed
```

## 8. 质量 hard fails

Phase 1A hard fail:

- unknown provider。
- missing trade calendar。
- duplicate `(symbol, dt, frequency)`。
- invalid OHLC。
- negative volume or amount。
- row after decision timestamp。
- adjusted research without factors。
- non-trading-day bars without explicit policy。
- stale latest session without blocked state。
- quality issue without report。
- manual repair without audit note。

## 9. Phase 1A 验收

Phase 1A 完成必须满足:

- Data lake paths and local secrets are ignored or guarded。
- Manifest/calendar 支持 A 股 exchange calendar。
- Tushare/AKShare/BaoStock provider probe matrix 存在。
- `510300.SH`、`510500.SH` 和 sample A 股 daily dataset 可构建。
- close/volume cross-check 产出 report。
- instruments、calendar、bars、adjustment 或 unavailability notes 存在。
- Quality report 覆盖 duplicate、missing OHLCV、non-trading day、missing latest session、missing adjustment factors。
- Manifest 记录 provider metadata、timezone、coverage、hashes、limitations。
- Snapshot 在 data audit 前保持 `curated_candidate`。

