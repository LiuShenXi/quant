# 03 · 数据、日历与多频

## 1. Dataset Manifest

每个研究数据集需要一个机器可读 manifest。最小字段:

```yaml
dataset_id: toy_multifreq_24x7_v1
source: test_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
symbols:
  - symbol: AAA-USD
    type: spot
    exchange: TEST
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: "PT4H"
  - freq: 1d
    file: bars_1d.csv
    expected_interval: "P1D"
```

manifest 的职责是把市场口径写进数据，而不是写进引擎常量。

## 2. Bars Schema

多频 bars 使用统一 schema:

| 字段 | 说明 |
| --- | --- |
| `symbol` | 标的代码 |
| `freq` | `1d`、`4h`、`1h` 等 |
| `dt` | bar 结束时间，必须 timezone-aware |
| `open/high/low/close` | 原始价格 |
| `volume` | base volume |
| `amount` | quote amount，可为空 |
| `quote_volume` | 可选，数据源提供时保留 |
| `data_status` | `ok` / `missing` / `no_trade` / `suspended` |
| `source` | 数据来源 |
| `updated_at` | 写入或导出时间 |

当前 `Bar.amount` 可先承载 quote amount；后续如要区分 `amount` 与 `quote_volume`，应通过向后兼容字段扩展。

## 3. 7x24 Calendar

新增 `continuous_24x7` calendar:

- 无周末/节假日休市假设。
- 预期 bar 由 `start/end/freq/timezone` 生成。
- daily boundary 默认 UTC 00:00，可由 manifest 改写。
- 缺失 4h bar 必须产生显式 quality issue，不能因为没有 A股 session 就跳过。

A股 calendar 仍保留原有交易日和连续竞价时段语义。

## 4. 多频无未来函数

多频原则:

```text
decision_time = 当前主频 bar 的结束时间
visible(freq) = 该 freq 下 dt <= decision_time 的最后已闭合 bar
history(freq) = 只包含 dt <= decision_time 的已闭合 bars
fill_time > signal_bar_time
```

示例: 主频 `4h`，辅助频 `1d`。

- `2026-01-02T04:00Z` 的 4h 决策不能看到 `2026-01-02T24:00Z` 日线。
- 它最多看到 `2026-01-01T24:00Z` 日线。
- report 需要记录本次决策使用的 daily confirmation timestamp。

## 5. Data Audit 要求

任何进入 backtest validation 的数据集至少需要:

- `(symbol, freq, dt)` 无重复。
- 每个 manifest 声明的 symbol/freq 在区间内的 expected bars 完整。
- 缺失、重复、时区不一致、source 不明要进入 deterministic audit summary。
- quote currency 明确。
- 7x24 数据不得复用 A股 holiday/session 规则。

数据审查结论缺失时，策略只能留在 research-only。
