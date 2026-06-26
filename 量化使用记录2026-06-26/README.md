# 量化使用记录 2026-06-26

本记录是一次非真实下单的系统使用痕迹，目标是用真实 ETF 数据跑通当前个人量化系统，并记录投资判断、运行证据与发现的问题。

## 数据来源

- 数据接口：AkShare `fund_etf_hist_sina`
- AkShare 文档：https://akshare.akfamily.xyz/data/fund/fund_public.html
- 本次数据区间：`2025-06-03T15:00:00+08:00` 到 `2026-06-25T15:00:00+08:00`
- 运行日期：`2026-06-26`
- 说明：截至本次刷新，最新日线停在 `2026-06-25`，这符合盘中或收盘前刷新时常见的数据状态；不把 `2026-06-26` 当作已完成交易日。

生成的数据根目录：

```text
量化使用记录2026-06-26/data/etf_510300_20250601_20260626/
量化使用记录2026-06-26/data/etf_510500_20250601_20260626/
```

## 本次运行资产

主观察资产：

```text
510300.SH / 沪深300ETF
```

横向探针资产：

```text
510500.SH / 中证500ETF
```

使用 510300 作为主观察资产的原因：

- ETF 流动性好，规则简单，适合先验证系统闭环。
- 避开个股退市、ST、长期停牌、成分股漂移等第一阶段噪声。
- 当前系统仍处于 Paper/真钱前观察阶段，不适合扩展到复杂组合或实盘。

## 回测结果

策略：`DualMA`

默认参数：

```text
fast: 20
slow: 60
target_qty: 10000
initial_cash: 100000
```

| 标的 | 策略收益 | 最大回撤 | 买入持有收益 | 订单 | 成交 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 510300.SH | -1.10% | -7.16% | 27.57% | 6 | 6 |
| 510500.SH | 5.86% | -14.21% | 59.30% | 5 | 5 |

结论：

- 双均线在这段趋势上涨样本里显著跑输买入持有。
- 参数邻域扫描没有给出足够稳健的生产信号。
- 本策略可以继续作为 Paper 管道验证策略，但不应作为收益型实盘策略推广。

参数扫描记录：

```text
量化使用记录2026-06-26/backtest/parameter_scan.csv
```

## Paper 运行结果

正常 replay：

```text
量化使用记录2026-06-26/paper/510300_normal/
```

结果：

```text
final state: NORMAL
ops status: NORMAL
orders: 5
trades: 5
event lines: 33
last reconciliation: OK
cash_diff: 0.0
```

期末账户快照：

```text
cash: 51571.36
position: 10000 shares of 510300.SH
avg_price: 4.755
market_value: 50480.00
total_value: 102051.36
```

断连演练：

```text
量化使用记录2026-06-26/paper/510300_disconnect_drill/
```

结果：

```text
final state: NORMAL
ops status: NORMAL
drill reconciliation: OK
engine transition: FREEZE_OPEN -> NORMAL
alerts: 1
cash_diff: 0.0
```

## 今日投资判断

这是研究与 Paper 账户结论，不是真实资金建议。

我不会把当前策略推入真钱交易。若以当前系统内的 Paper 账户为准，维持 510300 的观察仓位 `10000` 份，不加仓，不切换到 510500。

原因：

- 510300 Paper 运行链路稳定，核对为 OK，适合作为 M3b 观察对象。
- 510500 虽然部分参数收益更高，但买入持有涨幅更高，且波动和回撤更大；这更像市场 beta，不是策略 alpha。
- 当前回测引擎暴露出目标仓位和风控一致性问题，任何参数优化结论都必须降权。

下一步更像一个老派量化会做的事：继续 Paper 观察，先修系统可信度，再谈收益。

## 发现的问题

### P0：回测目标仓位会被未成交挂单打穿

现象：

- `DualMA` 目标仓位是 `10000` 份。
- 回测中出现连续买入导致持仓达到 `20000` 份。
- 在 5/20 参数复现中还出现净持仓 `-10000` 的路径。

证据：

```text
510300 20/60:
O-3 BUY 10000 created 2026-01-05, filled 2026-01-08
O-4 BUY 10000 created 2026-01-06, filled 2026-01-07
```

根因判断：

- `BacktestContext.set_target()` 只看当前持仓，不考虑 active/open orders。
- 回测下单不经过 Paper 路径里的 `ExecutionRouter`、`OMS`、`RiskEngine`。
- `Portfolio.apply_trade()` 对卖出没有阻止负持仓或负可卖。

影响：

- 回测和 Paper 交易序列不一致。
- 参数扫描收益和回撤可信度下降。
- 在修复前，不应基于回测结果做真钱决策。

### P1：回测缺少现金、可卖、仓位、风控约束

Paper 路径有风险检查：

```text
cash
sellable
max_order_value
max_position_value
gross_exposure
self_cross
trading_session
```

回测路径目前直接撮合订单，没有同等风控边界。建议让回测和 Paper 共用一套订单意图/风控语义，至少在回测中拒绝超现金买入和超可卖卖出。

### P1：回测与 Paper 撮合时序不一致

Paper replay 在 09:31 flush target，当日收盘成交；回测则在每根 bar 开始先撮合旧挂单，再运行策略生成新订单，通常下一根 bar 才可能成交。

影响：

- 同一策略在两条路径的订单数量、成交日期和收益不同。
- Paper 证据不能直接解释回测异常。

### P2：命令文档默认使用 `python`

本机环境中：

```text
python: command not found
python3: Python 3.13.3
.venv/bin/python: Python 3.13.3
```

建议 README 统一使用 `.venv/bin/python`，或补充 venv 激活说明。

### P2：裸 inline Python 需要 `PYTHONPATH=src:.`

脚本入口会手动插入路径，但直接运行诊断片段时 `import quant` 会失败。建议开发文档说明：

```bash
PYTHONPATH=src:. .venv/bin/python ...
```

或者将项目安装为 editable package。

### P2：Sina fallback 的数据语义需要持续标注

当前 fallback 可用，但仍有边界：

- 涨跌停价是按前收盘近似。
- 显式停牌行缺失。
- qfq 依赖累计分红合成。

建议 M3b 计数前继续抽查至少 10 个日期，并接入第二数据源做差异检测。

## 本次命令日志

```text
logs/01_build_510300.log
logs/02_backtest_510300.log
logs/03_paper_510300_normal.log
logs/04_ops_510300_normal.log
logs/05_build_510500.log
logs/06_backtest_510500.log
logs/07_paper_510300_disconnect_drill.log
logs/08_ops_510300_disconnect_drill.log
```
