# 实验 B4 - v1b 回撤控制 thesis 审查

Verdict: `CONTINUE_RESEARCH_ONLY_DRAWDOWN_CONTROL_THESIS`

## 目的

审查 `etf_regime_rotation_v1b_low_turnover` 是否值得从“收益增强 ETF 轮动”改写为“权益 ETF 仓位管理 / 回撤控制”研究假设。

本文件是 research-only 证据，不是 paper/live 准入，不是 QMT 接入建议，也不是交易参数推荐。

## Artifact

`artifacts/v1b_drawdown_control_thesis.json`

复现命令：

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
  .venv/bin/python research/runs/2026-07-01__etf_rotation_long_history_robustness/v1b_drawdown_control_thesis.py
```

固定口径：

```text
strategy = v1b representative cases, 20 bps slippage
benchmarks = fixed 60% equal-weight, fixed 60% 510300, fixed 60% 510500
rolling_window = 504 sessions
no parameter search
```

## 对 fixed 60% equal-weight

| Case | Return Gap | DD Improvement | Return Loss / DD Point |
| --- | ---: | ---: | ---: |
| v1b center | -10.7597% | 4.8614% | 2.2133 |
| v1b best20 | -6.9724% | 2.8743% | 2.4258 |

解释：

- v1b center 少赚 `10.7597` 个百分点，换来 `4.8614` 个百分点最大回撤改善。
- v1b best20 少赚较少，但最大回撤改善也更弱。
- 两者都不支持收益增强 thesis。
- 如果保留，只能作为“愿意牺牲收益以降低权益路径回撤”的研究假设。

## 504 日滚动窗口对 fixed 60% equal-weight

| 指标 | v1b center | v1b best20 |
| --- | ---: | ---: |
| windows | 1068 | 1068 |
| strategy negative windows | 568 | 571 |
| benchmark negative windows | 658 | 658 |
| negative window reduction | 90 | 87 |
| strategy higher return windows | 731 | 776 |
| strategy lower drawdown windows | 802 | 687 |
| drawdown improvement >= 3% windows | 517 | 396 |
| median return gap | 1.8748% | 2.0650% |
| median DD improvement | 2.5169% | 0.6674% |

解释：

- v1b center 在 `802/1068` 个 504 日窗口中回撤更低，且 `517` 个窗口回撤改善超过 3 个百分点。
- v1b center 比 fixed 60% equal-weight 少 `90` 个负收益窗口。
- v1b best20 的滚动收益相对更好，但回撤控制弱于 center。
- 因此若继续研究，center 比 best20 更适合作为回撤控制 thesis 的代表 case。

## 对 fixed 60% 510300

| Case | Return Gap | DD Improvement | Negative Window Reduction | Lower DD Windows |
| --- | ---: | ---: | ---: | ---: |
| v1b center | 0.3985% | 7.0067% | 69 | 735 |
| v1b best20 | 4.1858% | 5.0196% | 66 | 602 |

解释：

- 相对 fixed 60% 510300，v1b 同时有收益和回撤优势。
- 但 `510300` 不是本轮最强基准；不能用它单独证明策略有效。

## 对 fixed 60% 510500

| Case | Return Gap | DD Improvement | Negative Window Reduction | Lower DD Windows |
| --- | ---: | ---: | ---: | ---: |
| v1b center | -21.9178% | 9.0540% | 117 | 864 |
| v1b best20 | -18.1305% | 7.0669% | 114 | 845 |

解释：

- 相对 fixed 60% 510500，v1b 明显少赚，但显著降低最大回撤和负窗口数量。
- 这进一步支持“回撤控制工具”方向，而不是“收益增强 alpha”方向。

## CIO 判断

`etf_regime_rotation_v1b_low_turnover` 不能晋级为完整策略，也不能进入 paper。

但它可以继续作为 research-only 的回撤控制 thesis：

```text
在 A 股宽基 ETF 暴露中，低换手趋势/动量过滤可能用收益牺牲换取较低最大回撤、
较少 504 日负收益窗口，以及较低路径波动痛感。
```

阶段性判断：

- 收益增强 thesis：不成立。
- 回撤控制 thesis：可继续研究。
- 代表 case：优先用 v1b center，而不是 best20。
- paper/live/QMT/真钱：全部禁止。

## 下一步边界

允许继续：

```text
明确投资者适用场景：更关心回撤和持有体验，而不是追求最高收益；
加入现金基准、固定 40%/50%/60% 暴露基准，量化收益牺牲曲线；
检查回撤改善是否集中在少数窗口，还是稳定存在；
如果要保留 thesis，必须写出“不适用场景”：强牛市、风格持续单边上涨、对收益敏感账户。
```

停止条件：

```text
若相对 fixed 40%/50%/60% 简单暴露无法给出更好的回撤-收益交换，则停止 v1b 主线；
若回撤改善主要由少数年份贡献，且无法定义可识别 regime，则停止 v1b 主线；
若进一步真实成本或成交限制侵蚀回撤优势，则停止 v1b 主线。
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
