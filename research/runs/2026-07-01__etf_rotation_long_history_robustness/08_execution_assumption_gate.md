# 执行口径 Gate - ETF 轮动 v1

Verdict: `NO_PAPER_EXECUTION_GATE`

## 目的

把抽象的回测 flush 周期映射为真实可执行语义，并判断当前证据是否足以生成 paper observation plan。

本文件是 research-only 证据，不是 paper/live 准入，也不是交易建议。

## 当前可解释口径

当前 session-fixed baseline 对应以下语义：

```text
T 日收盘后形成信号；
T+1 交易日 09:31 附近按开盘价尝试成交；
日内不使用 T+1 收盘信息影响 T+1 开盘成交；
每日收盘后统一估值一次。
```

该口径比旧 `after_risk_fix` 和 `after_timeline_fix` artifact 更接近真实 paper 执行，因此当前只采用 `after_session_fix` 结果做决策。

## 当前证据

| Case | Return | Max DD | 解释 |
| --- | ---: | ---: | --- |
| cash | 0.0000% | 0.0000% | 不承担市场风险 |
| `510300.SH` buy-and-hold | 20.9689% | -45.1007% | 单 ETF 基准 |
| `510500.SH` buy-and-hold | 58.1627% | -47.3145% | 单 ETF 基准 |
| equal-weight hold | 39.5658% | -42.4382% | 简单分散基准 |
| strategy baseline | 18.4487% | -29.4192% | 当前真实执行候选口径 |
| strategy + 10 bps slippage | 4.1660% | -33.7168% | 中等滑点压力 |
| strategy + 20 bps slippage | -8.3175% | -37.7151% | 高滑点压力 |
| delay 1 + 0 bps | 55.3888% | -13.9848% | 延迟路径较强，但不能视为默认可执行优势 |

## Gate 判断

当前不满足 paper execution gate：

- baseline 收益低于 `510300.SH`、`510500.SH` 和等权持有。
- `10 bps` 滑点后收益接近现金，但仍承担 `-33.7168%` 最大回撤。
- `20 bps` 滑点后收益为负。
- 延迟一周期表现更强，说明策略对执行时点高度敏感；这不是稳健性证据，而是路径依赖警告。
- 尚未证明该策略在真实交易约束下提供足够的风险调整后优势。

## 下一步研究规则

进入下一轮研究前，必须先固定以下假设：

```text
signal_time = T close after all universe bars
order_time = T+1 open
fill_price_model = open price plus explicit slippage bps
equity_marking = daily close, one row per trading session
volume_cap = documented and enforced
comparison_set = cash, 510300 hold, 510500 hold, equal-weight hold
```

只有在固定口径下仍满足以下条件，才允许重新讨论 paper observation plan：

```text
return must exceed equal-weight or explain why lower return is acceptable;
max_drawdown reduction must be material and stable;
10 bps and 20 bps slippage cases must remain economically meaningful;
parameter perturbations must not depend on a single lucky setting;
all tests and artifact inspections must pass with zero unexplained rejects.
```

## CIO 结论

执行口径 gate 不通过。后续处置见 `09_cio_disposition_and_next_experiments.md`：原始 v1 降级为 research-only 素材，当前不生成 paper observation plan。
