# 数据审计 - 长历史 ETF 轮动数据集

Verdict: `PASS_WITH_WARNINGS`

## 审查数据集

`research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630`

用途：`etf_regime_rotation_v1` 的 research-only 长历史鲁棒性验证。

## 构建环境

使用项目虚拟环境：

```bash
.venv/bin/python -V
.venv/bin/python scripts/check_data_dependencies.py --module pandas --module akshare
```

结果：

```text
Python 3.13.3
pandas available: true
akshare available: true
status: PASS
```

已观察到系统 `python` 不存在，系统 `python3` 没有项目依赖。因此当前研究命令必须使用
`.venv/bin/python`。

## 构建命令

```bash
.venv/bin/python scripts/build_akshare_etf_data.py --symbol 510300.SH --name 300ETF --start-date 20200101 --end-date 20260630 --out research/datasets/akshare_510300_20200101_20260630

.venv/bin/python scripts/build_akshare_etf_data.py --symbol 510500.SH --name 500ETF --start-date 20200101 --end-date 20260630 --out research/datasets/akshare_510500_20200101_20260630

.venv/bin/python scripts/merge_etf_datasets.py --input research/datasets/akshare_510300_20200101_20260630 --input research/datasets/akshare_510500_20200101_20260630 --out research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630
```

命令输出摘要：

```text
510300 bars: 1571
510300 calendar days: 1571
510500 bars: 1571
510500 calendar days: 1571
merged bars: 3142
merged instruments: 2
merged adjust_factors: 3142
merged calendar days: 1571
```

## 已执行检查

```text
symbols=['510300.SH', '510500.SH']
bars_rows=3142
bars_min_dt=2020-01-02T15:00:00+08:00
bars_max_dt=2026-06-30T15:00:00+08:00
duplicate_symbol_dt=0
core_nulls={'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0, 'amount': 0}
data_status={'ok': 3142}
calendar_rows=1571
calendar_min=2020-01-02
calendar_max=2026-06-30
instrument_rows=2
adjust_factor_rows=3142
```

## Hashes

```text
bars_1d.csv
  SHA256=2E10C181D8DE397F2853B137A889094C6878311003253AE80D68A5BF0C197281
trade_calendar.csv
  SHA256=58D5F192D414A15BC60A19919A324BC12865ED3F1FC2B043C41DEB8965C59D66
instruments.csv
  SHA256=C7B16F2C03A7B3EC611CE69D211F1C1F3406E4077610D4ADB5AAD9FF03AFCB56
adjust_factors.csv
  SHA256=0149BE13CB633221DC17D661CB9FB6DB381198AD33B22603D4EF3F8B5F014D3B
```

## 警告

- 本次数据来自 AKShare provider，仍需在后续正式包中保存 provider 版本和原始命令日志。
- 本次数据可用于 research-only 长历史验证，不批准 paper/live。
- 若后续把策略推进到 paper，必须重新确认最新数据日期、构建日志、数据源函数和复权口径。
