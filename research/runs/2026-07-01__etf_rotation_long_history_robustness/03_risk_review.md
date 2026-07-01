# 风控审查 - ETF 轮动长历史

Decision: `APPROVE_FOR_REVIEW`

范围：仅批准继续 research-only 审查，不批准 paper/live。

## 已审查证据

- `config/risk/global.yaml`
- `research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/etf_regime_rotation_510300_510500.yaml`
- `src/quant/risk/pipeline.py`
- `src/quant/backtest/engine.py`
- 长历史回测 orders 拒单统计

## 当前边界

全局风险边界：

```text
max_order_value=200000
max_position_value_per_symbol=500000
max_gross_exposure_pct=0.95
daily_loss_freeze_pct=0.02
daily_loss_halt_pct=0.04
```

策略研究配置边界：

```text
target_exposure_pct=0.8
max_order_value=100000
max_position_value=100000
max_gross_exposure_pct=0.95
runtime_mode=backtest
```

## paper 阶段的风控阻塞项

- 初次长历史回测中 116 笔订单被 `max_order_value` 拒绝，说明目标调仓行为没有适配单笔风险上限。
- target 执行层切片后重跑，订单拒单为 0，未放宽风险上限。
- 不能通过放宽 `max_order_value` 来让回测结果更好看。
- 仍缺成本/滑点、延迟执行、参数稳定性和现金基准。
- 尚无 paper observation plan、M3b signoff package、paper/live gatekeeper review 或人工风险授权。

## 所需限额变化

Research-only 阶段不需要放宽风险限制。

订单切片已经在 target 执行层处理。下一步仍不应提高风险上限，应继续做敏感性和 paper 观察计划审查。

## 人工签核需求

继续研究不需要人工签核。任何 paper/live-adjacent、M4/QMT、券商接入、真钱、资金规模或风险边界变化都需要人工授权。
