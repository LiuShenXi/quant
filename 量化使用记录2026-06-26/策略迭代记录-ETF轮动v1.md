# ETF 轮动 v1 策略迭代记录

## 策略意图

用趋势过滤避免弱势市场，用相对强弱在 `510300.SH` 与 `510500.SH` 之间选择更强 ETF。该策略仍为研究策略，不进入真钱交易。

## 使用边界

- 没有修改框架代码。
- 外部策略代码保存在 `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation.py`。
- 外部策略配置保存在 `量化使用记录2026-06-26/strategy_lab/etf_regime_rotation_510300_510500.yaml`。
- 回测通过框架脚本 `scripts/run_backtest.py` 执行。

## 参数

```text
trend_window: 60
momentum_window: 20
target_exposure_pct: 0.8
min_hold_days: 5
score_buffer: 0.01
```

## 回测结果

```text
period: 2025-06-03T15:00:00+08:00 -> 2026-06-25T15:00:00+08:00
initial_cash: 100000.00
final_value: 120098.30
return_pct: 20.10%
max_drawdown_pct: -6.49%
orders: 25
trades: 25
rejected_orders: 0
```

对比：

```text
510300 buy-and-hold: 27.57%
510500 buy-and-hold: 59.30%
DualMA 510300 20/60: -1.10%, max drawdown -7.16%
DualMA 510500 20/60: 5.86%, max drawdown -14.21%
```

## 本轮迭代修正

初版轮动策略在 ETF 切换时同一天同时提交卖旧仓和买新仓，买单可能在旧仓资金释放前触发现金不足。外部策略已改成更保守的两段式换仓：

1. 先把旧 ETF 目标仓位设为 0。
2. 等账户变为空仓状态。
3. 下一交易日再买入新 ETF。

最终回测订单拒单数为 0。

## 投资判断

ETF 轮动 v1 比 DualMA 更值得继续研究，但不能直接进入真钱交易。

理由：

- 收益和回撤明显优于当前 DualMA 验证策略。
- 没有跑赢本轮最强的 510500 买入持有，不能证明具备稳定 alpha。
- 样本时间较短，需要更长历史区间和 Paper 观察。

下一步建议：

- 扩展到更长历史区间。
- 比较不同市场阶段：上涨、震荡、下跌。
- 继续保留 Paper 观察，不实盘。
