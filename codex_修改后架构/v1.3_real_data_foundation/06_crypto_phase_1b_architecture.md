# 06 · Crypto Phase 1B 架构

## 1. 启动条件

Phase 1B 只能在 Phase 1A 的 shared contracts 稳定后启动:

- data lake 四层结构稳定。
- manifest lifecycle schema 可用。
- hash and quality report contracts 可用。
- publication gate 可阻塞失败数据。
- provider probe command 模式可复用。

Crypto 不能 fork 出独立合同。它必须复用 Phase 1A 的 manifest、quality、audit 和 publication gate。

## 2. 最小 universe

第一批:

- `BTCUSDT`
- `ETHUSDT`
- `SOLUSDT`

可在 config 中映射不同 venue symbol,但 manifest 必须记录:

- canonical symbol。
- venue symbol。
- base asset。
- quote asset。
- venue。
- status。

## 3. Provider

Primary candidates:

- Binance public market data。
- OKX public market data。

Sanity sources:

- Coinbase public/advanced market data where accessible。
- Kraken public market data where accessible。

Provider probe 必须记录 interval support、history window、rate limit、timestamp semantics、symbol status 和返回字段。

## 4. 必需 dataset

| Dataset | 必需字段 | 用途 |
| --- | --- | --- |
| `instruments` | symbol, base asset, quote asset, venue, status, tick size, lot size, min notional | tradability and sizing assumptions |
| `bars_1d` | open time, close time, OHLC, volume, quote volume, trade count, source | daily research |
| `bars_4h` | open time, close time, OHLC, volume, quote volume, trade count, source | 4h research |
| `cross_source_prices` | symbol, timestamp, source, close, comparison result | venue sanity |
| `symbol_status` | symbol, effective time, trading status | listing/delisting awareness |

## 5. 时间戳政策

Crypto 时间戳必须同时表达 provider identity 和 engine decision time。

Policy:

- Provider identity key: exchange open time。
- Engine-facing decision time: fully closed bar boundary。
- Manifest must state whether `dt` stores open time, close time, or normalized decision timestamp。

推荐 staged schema:

```text
venue
symbol
frequency
open_time_utc
close_time_utc
decision_time_utc
open
high
low
close
volume
quote_volume
trade_count
source
data_status
updated_at
```

对于 4h, bar 只有在 close boundary 加确认延迟后才可用于 research/backtest。

## 6. Calendar

Crypto 使用 `continuous_24x7` calendar,不得复用 A 股 holiday logic。

Quality checks 必须覆盖:

- 4h interval completeness。
- 1d interval completeness。
- UTC boundary alignment。
- no duplicate `(venue, symbol, open_time, frequency)`。
- no future rows relative to decision timestamp。

## 7. Cross-source checks

Cross-source check 应比较:

- close price。
- timestamp alignment。
- quote currency。
- venue status。

差异处理:

- small venue spread: warning with threshold。
- missing sanity source: warning if primary source otherwise complete。
- material divergence: block or `FAIL`。
- symbol mismatch: mark unavailable, do not fabricate equivalent data。

## 8. Phase 1B Pipeline

```text
load crypto config
-> probe Binance and OKX
-> probe Coinbase/Kraken where accessible
-> fetch raw 4h/1d
-> normalize staged with open/close/decision times
-> build curated_candidate snapshot
-> run interval and cross-source quality checks
-> write manifest/hash/quality report
-> data audit verdict
-> publish research_ready only after gate
```

## 9. Phase 1B 验收

Phase 1B 完成必须满足:

- 复用 Phase 1A contracts。
- Binance 和 OKX adapters 可为 BTCUSDT、ETHUSDT、SOLUSDT 构建 4h/1d。
- Coinbase/Kraken sanity check 在可访问时记录。
- Manifest 记录 UTC semantics 和 decision-time policy。
- Quality report 捕捉 missing intervals、duplicate candles、invalid OHLC、negative volume、cross-source divergence。
- Provider 字段缺失进入 missing_fields,不能伪造成可用。

