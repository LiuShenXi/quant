# 11 · Testing 与 Acceptance

## 1. 测试目标

v1.3 测试重点不是 provider 能不能联网,而是合同、失败路径和门禁是否可靠。

测试必须证明:

- 不能把脏数据发布成 `research_ready`。
- 不能在缺 calendar/adjustment/provider/source 时通过。
- 不能让策略 import provider adapter。
- Provider 字段缺失会进入 manifest limitation。
- A 股和 crypto 时间语义不会混用。
- 旧 tests 不被 v1.3 schema 破坏。

## 2. Unit tests

Manifest:

- valid v1.3 manifest loads。
- missing schema version fails。
- `research_ready` without audit artifact fails。
- invalid lifecycle transition fails。
- missing provider source fails。
- missing hash fails。

Calendar:

- A 股 session calendar generates daily close timestamps。
- non-trading day bar is rejected。
- missing expected session is detected。
- crypto continuous 4h boundaries remain UTC。

Quality:

- duplicate keys fail。
- missing OHLCV fails。
- invalid OHLC fails。
- negative volume/amount fails。
- future row fails。
- stale latest session blocks。
- missing adjustment factors for adjusted research fails。

Security:

- token redaction removes env token values。
- metadata writer excludes secret fields。
- example config contains placeholders only。

## 3. Integration tests

Phase 1A synthetic fixtures:

- provider probe fixture with available and unavailable fields。
- raw -> staged -> curated_candidate -> quality report。
- A 股 calendar alignment。
- AKShare/BaoStock cross-check sample。
- quality fail prevents latest research_ready pointer update。

Phase 1B synthetic fixtures:

- crypto 4h/1d complete intervals。
- missing interval fail。
- cross-source divergence report。
- open_time vs decision_time semantics。

## 4. CLI tests

Commands should support dry-run:

- provider probe writes field matrix。
- ingest dry-run writes no published research_ready。
- audit command writes machine and markdown report。
- daily update failure keeps old snapshot pointer。

Expected failure tests are as important as success tests。

## 5. Import-boundary tests

Update strategy import checker if `quant.data_providers` is introduced:

- strategies cannot import `quant.data`。
- strategies cannot import `quant.data_providers`。
- strategies cannot import provider SDKs。
- `quant.core` cannot import data/backtest/live/risk。

## 6. Documentation tests

Docs acceptance:

- Runbook explains initial backfill。
- Runbook explains daily update。
- Runbook explains failed quality recovery。
- Docs state Phase 1 research-only boundary。
- Docs state provider permissions require probe。
- Docs state data audit required before backtest claim。

## 7. Phase 1A acceptance

Phase 1A is accepted only when:

- data lake and secret paths are gitignored or guarded。
- manifest/calendar supports A 股 exchange sessions。
- provider probe matrix exists for Tushare, AKShare, BaoStock。
- small A 股/ETF daily universe builds end to end。
- cross-source close/volume comparison report exists。
- dataset includes instruments, trade_calendar, bars, and adjustment info or explicit unavailability。
- quality report catches required negative cases。
- manifest records source, timezone, coverage, hashes, limitations。
- no snapshot becomes `research_ready` without data audit。

## 8. Phase 1B acceptance

Phase 1B is accepted only when:

- Phase 1A contracts are reused。
- Binance/OKX can build configured BTC/ETH/SOL 4h and 1d datasets。
- Coinbase/Kraken sanity records exist where accessible。
- manifest states UTC and decision-time policy。
- quality catches missing intervals、duplicate candles、invalid OHLC、negative volume、cross-source divergence。

## 9. Completion review checklist

Before declaring v1.3 implementation complete:

```text
[ ] Every dataset has manifest.
[ ] Every curated candidate has data hash.
[ ] Every curated candidate has quality result.
[ ] Every research-ready dataset has audit verdict.
[ ] Failed quality cannot update latest research-ready pointer.
[ ] Provider field matrix exists before ingestion depends on field.
[ ] Strategies cannot import providers.
[ ] Backtest artifacts record dataset manifest and verdict.
[ ] Docs/runbooks explain failure recovery.
[ ] No credentials or real provider outputs are tracked by git.
```

