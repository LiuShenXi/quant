# M3b 就绪状态

日期：2026-06-26

本文用来检查当前非真钱验证证据是否满足 M3b Paper 观察门槛。它不是 M3b 最终签字包。

## 当前证据

今日可计数观察记录：

```text
首轮量化使用记录/原始记录/observations/2026-06-26-510300-counted.md
```

每日台账：

```text
首轮量化使用记录/原始记录/observations/paper_daily_ledger.csv
```

当前状态快照：

```text
首轮量化使用记录/原始记录/observations/current_paper_status.md
```

今日可计数归档：

```text
runtime/observations/2026-06-26-510300-counted/
```

断线演练归档：

```text
runtime/observations/2026-06-26-510300-disconnect-drill/
```

## 门槛检查

| M3b 要求 | 当前状态 | 结果 |
|---|---|---|
| 同一策略配置以 `runtime_mode: paper` 运行 | 已使用 `dual_ma_510300_real_validation_paper.yaml` | 部分满足 |
| 至少 10 个交易日的 Paper 观察 | 当前只有 1 个可计数观察日 | 未满足 |
| 每个计数日都有日期、策略、账户、状态、订单、成交、拒单、对账、报警和备注 | 台账已有 1 行可计数记录 | 部分满足 |
| 每个计数日收盘对账零差异 | 2026-06-26 对账 `OK`，`cash_diff=0.0` | 当前日满足 |
| 没有未解决的引擎崩溃或缺失事件日志 | 今日事件日志和数据库已归档 | 当前日满足 |
| 完成断线演练 | 已完成 dry-run 演练，状态 `FREEZE_OPEN -> NORMAL` | 演练满足 |
| CRIT 报警包含必要字段 | dry-run 报警已产生 | 演练满足 |
| 手机端能看到 CRIT 报警并确认 | 只有 dry-run-file，没有手机侧确认 | 未满足 |
| 最终人工签字 `m3b_signoff.yaml` | 尚未生成 | 未满足 |
| `validate_m3b_signoff.py` 输出 `M4a may start` | 尚未对真实签字包运行 | 未满足 |

## 当前证据摘要

今日可计数 Paper：

```text
event_lines: 33
orders: 5
trades: 5
active_orders: 0
close_reconciliation: OK
cash_diff: 0.0
position_diffs: {}
account_diffs: {}
position_value_diffs: {}
alerts: 0
```

断线演练：

```text
event_lines: 16
orders: 1
trades: 1
active_orders: 0
state_transition: FREEZE_OPEN -> NORMAL
close_reconciliation: OK
cash_diff: 0.0
CRIT alerts: 1
alert_delivery_channel: dry-run-file
alert_delivery_id: delivery-12
```

## 决定

M3b 还没有准备好签字。

现在只能说：非真钱验证已经开始，并且已有 `1 / 10` 个可计数观察日。

还缺：

1. 继续积累 9 个可计数交易日。
2. 每天都要有完整台账和归档。
3. 补齐手机端 CRIT 报警确认。
4. 生成真实人工签字包。
5. 用校验脚本验证签字包通过。

## 下一步操作

继续使用：

```text
config/strategies/dual_ma_510300_real_validation_paper.yaml
config/paper_real_510300.yaml
```

每个可计数交易日都归档：

```text
runtime/paper_real_510300/meta.db
runtime/paper_real_510300/events.jsonl
当日操作记录
```

不要从当前证据启动 M4/QMT/真钱交易。
