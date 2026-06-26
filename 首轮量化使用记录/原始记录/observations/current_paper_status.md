# 当前 Paper 验证状态

更新时间：2026-06-26 17:25 CST

这是非真钱验证期的状态快照，不是 M3b 最终签字。

## 当前结论

`510300.SH` 今天已经完成 1 次可计数 Paper 观察。

关键证据：

```text
最新完整日线: 2026-06-26T15:00:00+08:00
数据来源: akshare:fund_etf_hist_sina+tx_daily+fund_etf_spot_em
Paper 最终状态: NORMAL
订单: 5
成交: 5
未完成订单: 0
收盘对账: OK
cash_diff: 0.0
报警: 0
归档目录: runtime/observations/2026-06-26-510300-counted/
```

## 数据健康

主数据目录：

```text
data_real/etf_510300_2025_2026_check/
```

最新检查：

```text
bars: 260
calendar_days: 260
first_bar: 2025-06-03T15:00:00+08:00
latest_bar: 2026-06-26T15:00:00+08:00
duplicates: 0
bad_ohlc: 0
non_positive_price: 0
non_positive_volume_or_amount: 0
missing_status: 0
latest_source: akshare:fund_etf_hist_sina+tx_daily+fund_etf_spot_em
```

数据文件哈希：

```text
a111bc21ce6a4e193e6c132813b2e7bc2b8496ced4f0286c7bcf72f59078fb79  data_real/etf_510300_2025_2026_check/bars_1d.csv
6043d27b6f1ff5ccae2c9b41e7194d8f8e244bf37d6f48e990efa61375958f1e  data_real/etf_510300_2025_2026_check/adjust_factors.csv
ffbbb9d2d79a6f0cf8a355a35a0cd5d50ec4827d5f1e109a7c57b739c62b1653  data_real/etf_510300_2025_2026_check/trade_calendar.csv
```

## 今日 Paper 证据

```text
runtime/observations/2026-06-26-510300-counted/events.jsonl
runtime/observations/2026-06-26-510300-counted/meta.db
```

归档哈希：

```text
57a9cadef3a9b8c9a64d6e7fbece511bcda448e07348792b686fd24351a9d416  runtime/observations/2026-06-26-510300-counted/events.jsonl
86a63546875837ae3f64cb33c327c95fb1dcf99775f229f3f93c1fb6d7d32518  runtime/observations/2026-06-26-510300-counted/meta.db
```

每日台账：

```text
首轮量化使用记录/原始记录/observations/paper_daily_ledger.csv
```

当前台账状态：

```text
非计数演练行: 3
可计数观察行: 1
M3b 进度: 1 / 10
```

## 下一步

继续每日 Paper 观察。每个交易日都要等完整日线可用后再跑，并继续归档事件日志、数据库和台账。

仍然不要启动 M4、QMT 或真钱交易。
