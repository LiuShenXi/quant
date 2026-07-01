# CIO 处置与下一实验计划 - ETF 轮动 v1

Decision: `DEMOTE_TO_RESEARCH_MATERIAL`

## 处置结论

`etf_regime_rotation_v1` 不进入 paper，不进入 live，不接 QMT，不使用真钱。

当前把它从“候选策略”降级为“研究素材”。它仍可用于提炼 ETF 轮动和风控参与的假设，但不能继续以原始 v1 形态争取 paper gate。

## 处置依据

session-fixed 真实执行口径下：

| 项目 | 结果 |
| --- | ---: |
| baseline return | 18.4487% |
| baseline max drawdown | -29.4192% |
| `510300.SH` buy-and-hold return | 20.9689% |
| `510500.SH` buy-and-hold return | 58.1627% |
| equal-weight hold return | 39.5658% |
| 10 bps slippage return | 4.1660% |
| 20 bps slippage return | -8.3175% |
| first-half strategy return | -2.1854% |
| second-half strategy return | 20.5907% |

主要问题：

- 收益低于 `510300.SH`、`510500.SH` 和等权持有。
- 前半段样本收益为负。
- 高滑点压力下收益为负，回撤仍接近权益风险水平。
- 延迟一周期结果显著更好，说明结果高度依赖执行时点，不能作为稳健 alpha 证据。
- 原策略仍在历史 `strategy_lab`，不是正式策略模块。

## 保留价值

该研究仍有价值，但价值不在原始 v1 策略本身，而在以下素材：

- 回测引擎已经暴露并修复了 target 切片、风控减仓、时间线、跨标的撮合、session 估值问题。
- ETF 轮动确实可能降低部分路径的最大回撤。
- 执行时点对结果影响很大，说明未来研究必须先定义可执行口径，再看收益。
- 参数扰动显示存在研究空间，但当前不能用单参数最优结果替代策略结论。

## 下一轮可证伪实验

下一轮只保留三类 research-only 实验。任何实验若未能通过固定执行口径，不得进入 paper 讨论。

### 实验 A：风险关闭基准

目的：验证“低回撤”是否来自有效择时，还是只是长期空仓/低暴露。

固定口径：

```text
signal_time = T close
order_time = T+1 open
slippage = 10 bps and 20 bps
equity_marking = daily close
comparison = cash, 510300 hold, 510500 hold, equal-weight hold
```

通过条件：

```text
10 bps 后收益必须显著高于现金；
20 bps 后不得为负；
最大回撤相对等权必须有明确改善。
```

### 实验 B：低换手轮动约束

目的：检查策略是否能通过降低换手来保留回撤优势，并缓解滑点压力。

允许改动：

```text
increase min_hold_days;
increase score_buffer;
reduce target_exposure_pct;
keep universe fixed to 510300.SH and 510500.SH.
```

禁止改动：

```text
不得扩大标的池；
不得使用未来数据；
不得调参直到超过单个历史窗口最优。
```

通过条件：

```text
baseline return >= equal-weight return or clear risk-adjusted explanation;
20 bps slippage return > 0;
max drawdown materially below equal-weight;
sample split 不得出现一半样本完全失效。
```

### 实验 C：重定义策略 thesis

目的：如果收益增强 thesis 不成立，检查是否可以把方向重定义为“回撤控制/权益仓位管理”。

候选 thesis：

```text
在 A 股 ETF 暴露中，动量/趋势过滤可能作为权益仓位管理工具，而不是收益增强 alpha。
```

通过条件：

```text
必须与现金、等权、单 ETF、固定 60% 暴露基准比较；
必须报告收益损失换来的回撤改善；
必须明确适用场景和不适用场景。
```

## 立即停止条件

出现以下任一情况，停止该主线：

- 固定真实执行口径下，20 bps 滑点长期为负。
- 低换手约束后收益和回撤都弱于简单基准。
- 策略优势只来自某一个参数或某一个样本半区。
- 再次发现引擎 bug，先暂停研究并修复验证。

## 当前 CIO 状态

```text
strategy_status = DEMOTE_TO_RESEARCH_MATERIAL
paper_gate = FAIL
live_gate = FAIL
next_action = research-only falsification experiments
```

本处置不是投资建议，也不是交易许可。
