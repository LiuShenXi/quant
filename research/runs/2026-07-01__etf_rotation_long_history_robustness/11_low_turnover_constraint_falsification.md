# 实验 B - 低换手约束证伪

Verdict: `CONTINUE_RESEARCH_ONLY_LOW_TURNOVER_VARIANT`

## 目的

检查 `etf_regime_rotation_v1` 的低换手约束变体是否仍被固定暴露基准击败，或是否值得作为新的 research-only 假设继续研究。

本文件不是 paper/live 准入，也不是参数推荐。

## Artifact

`artifacts/low_turnover_constraint_falsification.json`

固定规则：

```text
universe = 510300.SH, 510500.SH
signal_time = T close
order_time = T+1 open
equity_marking = daily close, one row per session
slippage = 0 bps, 10 bps, 20 bps
comparison_gate = equal-weight fixed 60%
```

硬门槛：

```text
0 bps return >= equal-weight fixed 60% return 23.7395%;
0 bps max drawdown no worse than equal-weight fixed 60% max drawdown -28.4041%;
20 bps return > 0;
no half-sample failure;
rejected_orders = 0.
```

## 通过 case

| Case | Return 0 bps | Max DD 0 bps | Return 20 bps | Max DD 20 bps | Orders | Turnover | Avg Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `score_buffer_0_03` | 28.3048% | -23.1817% | 6.6566% | -30.2152% | 117 | 101.0414x | 47.9147% |
| `score_buffer_0_05` | 27.7142% | -24.3258% | 8.9932% | -30.7868% | 104 | 88.2076x | 48.6568% |
| `exposure_0_6_hold_40_buffer_0_05` | 26.1822% | -19.0827% | 12.9798% | -23.5427% | 93 | 60.7123x | 37.2802% |

## 最值得继续审查的变体

`exposure_0_6_hold_40_buffer_0_05`

参数：

```text
trend_window=60
momentum_window=20
target_exposure_pct=0.6
min_hold_days=40
score_buffer=0.05
```

理由：

- 20 bps 滑点后收益最高：`12.9798%`。
- 0 bps 最大回撤最低：`-19.0827%`。
- 20 bps 最大回撤为 `-23.5427%`，优于固定 60% 等权的 `-28.4041%`。
- 订单数从原始 v1 的 `161` 降到 `93`。
- 换手从原始 v1 的 `133.7814x` 降到 `60.7123x`。

样本拆分：

| Slippage | First Half Return | First Half Max DD | Second Half Return | Second Half Max DD |
| ---: | ---: | ---: | ---: | ---: |
| 0 bps | 5.2731% | -16.2482% | 19.4873% | -13.3044% |
| 20 bps | -1.2058% | -18.8482% | 14.0007% | -14.1844% |

警告：20 bps 下前半段仍为负，虽然没有触发“半段完全失效”的停止条件，但说明该变体还没有通过稳健性审查。

## 未通过 case 的意义

- `baseline_reference` 未通过：20 bps 收益 `-8.3175%`。
- `min_hold_20` 未通过：0 bps 收益未超过固定 60% 等权，20 bps 收益为负。
- `exposure_0_6` 未通过：降低暴露本身不能解决问题。
- `exposure_0_6_hold_20_buffer_0_03` 未通过：回撤好，但收益不够。

## CIO 判断

原始 `etf_regime_rotation_v1` 仍维持 `DEMOTE_TO_RESEARCH_MATERIAL`。

允许新增一个 research-only 低换手变体假设：

```text
etf_regime_rotation_v1b_low_turnover
```

它不是 paper 候选策略，只是下一轮研究对象。下一轮必须做：

```text
独立样本/滚动窗口稳定性；
更真实成交成本；
与固定 60% 等权和固定 60% 510300/510500 对比；
参数邻域稳定性，而不是单点最优。
```

## 当前限制

不得 paper，不得 live，不得 QMT，不得真钱。不得把本实验中的通过 case 作为参数推荐。
