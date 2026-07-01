# 回测审查 - ETF 轮动长历史

Verdict: `PASS_WITH_WARNINGS`

审查回测：

`research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history`

请求决策：判断长历史 artifact 是否可作为 research-only 证据，不是 paper 准入。

## 回测命令

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
.venv/bin/python scripts/run_backtest.py \
  --strategy research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/etf_regime_rotation_510300_510500.yaml \
  --data-root research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630 \
  --out research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history \
  --initial-cash 100000
```

策略代码仍来自历史 `strategy_lab`，本次没有把它晋级到正式 `strategies/` 包。

## 引擎修复说明

旧版长历史 baseline 已作废，不再用于绩效判断。原因是发现并修复了三个回测引擎问题：

- 多标的日线处理按单根 bar 推进，可能让某标的收盘信号在另一标的同日开盘执行，形成时间倒置。
- `_match_open_orders()` 未按订单标的过滤，跨标的订单可能被错误 bar 撮合。
- 多标的日线 equity 每个标的记录一次，且首个标的 `on_bar` 无法看到其他标的开盘成交和全市场收盘估值。

修复后已补回归测试，并重跑本页 artifact。旧 `88.5743%` 和 `28.0922%` baseline 只能作为 bug 审计线索，不能作为策略证据。

## Artifact 完整性检查

```text
status=PASS
blocking_issues=[]
warnings=[]
orders_rows=161
trades_rows=161
equity_rows=1571
events_rows=322
invalid_event_rows=0
```

## 核心报告

```text
period_start=2020-01-02T15:00:00+08:00
period_end=2026-06-30T15:00:00+08:00
initial_value=100000.00
final_value=118448.70
return_pct=18.4487
max_drawdown_pct=-29.4192
total_commission=3344.50
orders_rows=161
orders_rejected=0
trades_rows=161
```

## 基准对比

Method: `close_to_close_normalized_buy_and_hold`

| Benchmark | Return | Max drawdown |
| --- | ---: | ---: |
| `510300.SH` buy-and-hold | 20.9689% | -45.1007% |
| `510500.SH` buy-and-hold | 58.1627% | -47.3145% |
| normalized equal-weight hold | 39.5658% | -42.4382% |
| `etf_regime_rotation_v1` session-fixed backtest | 18.4487% | -29.4192% |

## 样本拆分

| Split | Strategy return | Strategy max DD | Equal-weight return | 510300 return | 510500 return |
| --- | ---: | ---: | ---: | ---: | ---: |
| first half, 2020-01-02 to 2023-03-29 | -2.1854% | -23.9863% | 2.1765% | -3.6635% | 8.0165% |
| second half, 2023-03-30 to 2026-06-30 | 20.5907% | -13.1262% | 34.9459% | 24.2327% | 45.6591% |

## 可信度阻塞项

初次长历史回测中有 116 笔订单被 `max_order_value` 风控拒绝；target 执行层切片后该问题已修复。

但后续时间线、跨标的撮合、session 处理 bug 修复显著改变绩效结论。修复后的策略收益低于 `510300.SH`、`510500.SH` buy-and-hold 和等权持有，最大回撤也不再显著优于所有基准。

本次长历史结果可继续作为 research-only 证据，但不支持 paper 准入。

## 后续必需检查

- 明确真实 paper 可执行的成交时点和滑点假设。
- 将当前策略与现金、等权、单 ETF 持有、低风险关闭状态放在同一决策框架内比较。
- 继续参数稳定性研究，但禁止把单参数扰动最好结果当作推荐参数。
