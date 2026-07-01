# 实验 B6 - v1b 路径平滑效用审查

Verdict: `RETIRE_V1B_MAINLINE`

## 目的

检验 `etf_regime_rotation_v1b_low_turnover` 最后剩余的 research-only 命题：

```text
v1b 是否能稳定减少长期滚动窗口的负收益次数，从而提供路径平滑效用？
```

本文件是 research-only 证据，不是 paper/live 准入，不是 QMT 接入建议，也不是交易参数推荐。

## Artifact

`artifacts/v1b_path_smoothing_utility.json`

复现命令：

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
  .venv/bin/python research/runs/2026-07-01__etf_rotation_long_history_robustness/v1b_path_smoothing_utility.py
```

固定口径：

```text
strategy = v1b center and v1b best20, 20 bps slippage
benchmarks = fixed 40%/50%/60% equal-weight and fixed 40%/50%/60% 510500
rolling_windows = 252, 504, 756 sessions
no parameter search
```

## 核心结论

v1b 的负收益窗口优势不稳定，只存在于 504 日窗口。

相对 fixed 40%/50%/60% equal-weight 的负收益窗口减少数量：

| Strategy | 252 sessions | 504 sessions | 756 sessions |
| --- | ---: | ---: | ---: |
| v1b center | -23 | 90 | -88 |
| v1b best20 | -24 | 87 | -36 |

解释：

- 正数表示 v1b 的负收益窗口更少。
- 负数表示 v1b 的负收益窗口更多。
- v1b 在 252 日和 756 日窗口下均没有路径平滑优势。
- 因此“减少长期负收益窗口”不是稳定效用，而是依赖 504 日窗口定义。

## 252 日窗口

| Portfolio | Negative Windows | Negative Window % | Median Return | Worst Window Return |
| --- | ---: | ---: | ---: | ---: |
| v1b center | 677 | 51.2879% | -1.0694% | -16.6106% |
| v1b best20 | 678 | 51.3636% | -1.3066% | -19.1107% |
| fixed 40% equal-weight | 654 | 49.5455% | 0.8306% | -13.3372% |
| fixed 50% equal-weight | 654 | 49.5455% | 1.0249% | -16.1758% |
| fixed 60% equal-weight | 654 | 49.5455% | 1.2146% | -18.8504% |

解释：

- 一年期滚动窗口中，v1b 的负收益窗口更多。
- v1b center 的中位滚动收益为负，而 fixed 40/50/60 equal-weight 均为正。
- 这不支持“持有体验更平滑”的命题。

## 504 日窗口

| Portfolio | Negative Windows | Negative Window % | Median Return | Worst Window Return |
| --- | ---: | ---: | ---: | ---: |
| v1b center | 568 | 53.1835% | -1.1376% | -21.7476% |
| v1b best20 | 571 | 53.4644% | -1.5220% | -23.4894% |
| fixed 40% equal-weight | 658 | 61.6105% | -2.9738% | -18.0633% |
| fixed 50% equal-weight | 658 | 61.6105% | -3.7142% | -22.0136% |
| fixed 60% equal-weight | 658 | 61.6105% | -4.4258% | -25.7708% |

解释：

- 两年期滚动窗口中，v1b 的负收益窗口确实更少。
- 但该优势不能外推到 252 和 756 日窗口。
- 单一窗口优势不能支撑独立投资效用。

## 756 日窗口

| Portfolio | Negative Windows | Negative Window % | Median Return | Worst Window Return |
| --- | ---: | ---: | ---: | ---: |
| v1b center | 608 | 74.5098% | -5.0789% | -19.2266% |
| v1b best20 | 556 | 68.1373% | -4.3807% | -20.6541% |
| fixed 40% equal-weight | 520 | 63.7255% | -6.5756% | -18.1051% |
| fixed 50% equal-weight | 520 | 63.7255% | -8.0861% | -22.0506% |
| fixed 60% equal-weight | 520 | 63.7255% | -9.5486% | -25.7987% |

解释：

- 三年期滚动窗口中，v1b 的负收益窗口更多。
- v1b center 的 median return 高于固定等权，但负窗口数量不占优。
- 如果把效用定义为“少出现长期负收益窗口”，v1b 不通过。

## CIO 判断

`etf_regime_rotation_v1b_low_turnover` 主线应退休。

逐步证伪链条：

```text
收益增强 thesis：不成立；
最大回撤-收益效率 thesis：被 fixed 40%/50% 简单暴露削弱；
路径平滑 / 负窗口减少 thesis：只在 504 日窗口成立，在 252 和 756 日窗口不成立。
```

因此，v1b 不再作为候选策略、paper 候选、QMT 接入对象或真钱交易对象推进。

## 保留价值

v1b 可保留为研究素材：

```text
低换手和 score buffer 可降低换手；
趋势/动量过滤在某些窗口能减少负收益期；
但这些效果不足以形成稳定、可执行、可解释的策略 thesis。
```

## 后续动作

允许：

```text
归档 v1b 研究包；
把有用结论抽取为未来 ETF 仓位管理研究的反例约束；
若另起新主线，必须先定义新的 thesis，不得从 v1b 参数继续追逐。
```

禁止：

```text
不得 paper；
不得 live；
不得接 QMT；
不得真钱交易；
不得继续扩大 v1b 参数搜索；
不得把 v1b center 或 best20 作为推荐参数。
```
