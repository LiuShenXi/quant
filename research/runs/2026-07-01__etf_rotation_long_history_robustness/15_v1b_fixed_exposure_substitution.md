# 实验 B5 - v1b 简单固定暴露替代审查

Verdict: `HOLD_FOR_PATH_SMOOTHING_UTILITY_REVIEW`

## 目的

检验 `etf_regime_rotation_v1b_low_turnover` 的回撤控制 thesis 是否能战胜更简单的固定暴露方案。

本文件是 research-only 证据，不是 paper/live 准入，不是 QMT 接入建议，也不是交易参数推荐。

## Artifact

`artifacts/v1b_fixed_exposure_substitution.json`

复现命令：

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
  .venv/bin/python research/runs/2026-07-01__etf_rotation_long_history_robustness/v1b_fixed_exposure_substitution.py
```

固定口径：

```text
strategy = v1b center and v1b best20, 20 bps slippage
benchmarks = fixed 40%/50%/60% equal-weight, fixed 40%/50%/60% 510300, fixed 40%/50%/60% 510500
benchmark = close-to-close normalized fixed exposure + cash
rolling_window = 504 sessions
no parameter search
```

## 关键对照

| Portfolio | Return | Max DD | 504d Negative Windows | Return / Abs Max DD |
| --- | ---: | ---: | ---: | ---: |
| v1b center | 12.9798% | -23.5427% | 568 | 0.5513 |
| v1b best20 | 16.7671% | -25.5298% | 571 | 0.6568 |
| fixed 40% equal-weight | 15.8263% | -20.0967% | 658 | 0.7875 |
| fixed 50% equal-weight | 19.7829% | -24.3739% | 658 | 0.8116 |
| fixed 60% equal-weight | 23.7395% | -28.4041% | 658 | 0.8358 |

解释：

- fixed 40% equal-weight 同时高于 v1b center 的收益、低于 v1b center 的最大回撤。
- fixed 50% equal-weight 同时高于 v1b best20 的收益、低于 v1b best20 的最大回撤。
- 因此 v1b 不能再被描述为“最大回撤-收益效率优于简单暴露”。
- v1b 唯一保留价值是 504 日负收益窗口更少：center 比 equal-weight 固定暴露少 `90` 个负窗口，best20 少 `87` 个负窗口。

## 替代审查结果

严格三条件支配定义：

```text
fixed exposure return >= strategy return;
fixed exposure max drawdown no worse than strategy max drawdown;
fixed exposure 504d negative windows <= strategy negative windows.
```

结果：

| Strategy | Strictly Dominating Fixed Cases | Higher Return + Lower Max DD Cases | Fixed Cases With Fewer/Equal Negative Windows |
| --- | --- | --- | --- |
| v1b center | none | fixed 40% equal-weight; fixed 40% 510500 | none |
| v1b best20 | none | fixed 40% 510500; fixed 50% equal-weight | none |

解释：

- 没有固定暴露方案在三项指标上严格支配 v1b。
- 但已有简单固定暴露在“收益 + 最大回撤”二维上优于 v1b。
- v1b 的剩余研究价值被迫收窄为“负收益窗口减少 / 路径平滑”，而不是“回撤-收益效率”。

## 对 510500 固定暴露

| Portfolio | Return | Max DD | 504d Negative Windows | Return / Abs Max DD |
| --- | ---: | ---: | ---: | ---: |
| fixed 40% 510500 | 23.2651% | -23.4706% | 685 | 0.9912 |
| fixed 50% 510500 | 29.0814% | -28.2092% | 685 | 1.0309 |
| fixed 60% 510500 | 34.8976% | -32.5967% | 685 | 1.0706 |

解释：

- fixed 40% 510500 与 v1b center 的最大回撤几乎相同，但收益高出 `10.2853` 个百分点。
- 它的负收益窗口更多，说明 v1b 的优势不是收益效率，而是较少长期负窗口。
- 如果投资者不显式重视“504 日窗口为负的次数”，v1b 没有保留理由。

## CIO 判断

`etf_regime_rotation_v1b_low_turnover` 的 broad drawdown-control thesis 被简单固定暴露明显削弱。

当前只能保留一个更窄的 research-only 命题：

```text
v1b 可能减少较长滚动窗口的负收益次数，但不能证明比简单固定暴露有更好的收益-最大回撤效率。
```

阶段性判断：

- 收益增强 thesis：不成立。
- 最大回撤-收益效率 thesis：不成立。
- 路径平滑 / 负窗口减少 thesis：待证伪。
- paper/live/QMT/真钱：全部禁止。

## 下一步边界

允许继续：

```text
只检验“负收益窗口减少”是否有独立投资意义；
定义投资者效用：是否愿意放弃全周期收益和收益/回撤效率，换取较少 504 日负窗口；
检查负窗口减少是否稳定存在于不同窗口长度，例如 252/504/756 sessions；
若该效用无法被清楚定义，应停止 v1b 主线。
```

停止条件：

```text
如果 252/504/756 窗口下负收益窗口优势不稳定，则停止 v1b 主线；
如果路径平滑无法转化为明确投资者适用场景，则停止 v1b 主线；
如果简单 fixed 40% equal-weight 已满足目标风险体验，则停止 v1b 主线。
```

禁止事项：

```text
不得 paper；
不得 live；
不得接 QMT；
不得真钱交易；
不得扩大参数搜索追逐历史最优；
不得把 v1b center 或 best20 作为推荐参数。
```
