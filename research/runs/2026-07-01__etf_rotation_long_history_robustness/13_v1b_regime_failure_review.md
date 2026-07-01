# 实验 B3 - v1b 失效区间 regime 归因

Verdict: `HOLD_FOR_DRAWDOWN_CONTROL_THESIS_REVIEW`

## 目的

解释 `etf_regime_rotation_v1b_low_turnover` 在 2021-2023 连续负年度的来源：这是策略独有失效，还是宽基 ETF 本身的弱 regime。

本文件是 research-only 证据，不是 paper/live 准入，不是 QMT 接入建议，也不是交易参数推荐。

## Artifact

`artifacts/v1b_regime_failure_review.json`

复现命令：

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
  .venv/bin/python research/runs/2026-07-01__etf_rotation_long_history_robustness/v1b_regime_failure_review.py
```

固定口径：

```text
strategy = v1b representative cases, 20 bps slippage
benchmarks = close-to-close normalized fixed 60% exposure + cash
benchmark set = fixed 60% equal-weight, fixed 60% 510300, fixed 60% 510500
no parameter search
```

## 全周期对照

| Portfolio | Return | Max DD |
| --- | ---: | ---: |
| v1b center 20 bps | 12.9798% | -23.5427% |
| v1b best20 20 bps | 16.7671% | -25.5298% |
| fixed 60% equal-weight | 23.7395% | -28.4041% |
| fixed 60% 510300 | 12.5813% | -30.5494% |
| fixed 60% 510500 | 34.8976% | -32.5967% |

解释：

- v1b center 的全周期收益略高于 fixed 60% 510300，但低于 fixed 60% equal-weight 和 fixed 60% 510500。
- v1b 的最大回撤优于三个固定 60% 基准。
- 收益增强 alpha 仍未成立；更合理的研究方向只能是“用收益牺牲换回撤控制”。

## 2021-2023 失效区间

| Portfolio | Return | Max DD |
| --- | ---: | ---: |
| v1b center 20 bps | -15.9617% | -23.5427% |
| v1b best20 20 bps | -16.9153% | -25.5298% |
| fixed 60% equal-weight | -18.8277% | -23.7833% |
| fixed 60% 510300 | -22.6543% | -28.4381% |
| fixed 60% 510500 | -14.8936% | -25.9023% |

解释：

- 2021-2023 不是策略单独失效；固定 60% equal-weight 和 510300 也为负。
- v1b center 在 2021-2023 合计收益略优于 fixed 60% equal-weight，主要来自 2022 熊市防守。
- 但 v1b 没有优于 fixed 60% 510500，说明它没有稳定选出更强宽基 ETF。

## 年度拆解

| 年份 | v1b center | v1b best20 | fixed 60% equal-weight | fixed 60% 510300 | fixed 60% 510500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 8.7667% | 10.1152% | 14.5763% | 16.4570% | 12.6957% |
| 2021 | -0.6010% | -0.7344% | 2.8510% | -4.0247% | 9.9200% |
| 2022 | -9.6685% | -9.5854% | -16.7424% | -13.5637% | -19.5876% |
| 2023 | -6.6066% | -7.6631% | -5.6171% | -6.7014% | -4.5809% |
| 2024 | 13.7548% | 16.0514% | 6.1442% | 9.1494% | 3.3503% |
| 2025 | 2.0497% | 2.2489% | 16.6106% | 12.6442% | 20.5102% |
| 2026 | 4.3637% | 5.0930% | 7.3768% | 2.2996% | 12.0165% |

相对 fixed 60% equal-weight：

| 年份 | v1b center excess | v1b best20 excess |
| --- | ---: | ---: |
| 2020 | -5.8096% | -4.4611% |
| 2021 | -3.4520% | -3.5854% |
| 2022 | 7.0739% | 7.1570% |
| 2023 | -0.9895% | -2.0460% |
| 2024 | 7.6106% | 9.9072% |
| 2025 | -14.5609% | -14.3617% |
| 2026 | -3.0131% | -2.2838% |

解释：

- v1b 真正有相对优势的年份是 2022 和 2024。
- 2021 没有捕捉到 510500 的强势，2025 也显著低于固定暴露。
- 这更像是某些 regime 下的防守/择时收益，而不是稳定轮动 alpha。

## 504 交易日滚动窗口

| 指标 | v1b center | v1b best20 |
| --- | ---: | ---: |
| windows | 1068 | 1068 |
| strategy min return | -21.7476% | -23.4894% |
| strategy median return | -1.1376% | -1.5220% |
| strategy max return | 26.5224% | 31.0382% |
| strategy negative windows | 568 | 571 |
| underperform fixed 60% equal-weight windows | 337 | 292 |
| fixed 60% equal-weight negative windows | 658 | 658 |
| underperform fixed 60% 510300 windows | 381 | 342 |
| underperform fixed 60% 510500 windows | 442 | 437 |

解释：

- v1b 相对 fixed 60% equal-weight 并非一直弱，滚动窗口中多数时候能跑赢等权固定暴露。
- 但 v1b 自身仍有超过一半的 504 交易日窗口为负收益。
- 这说明它可能有“降低固定暴露路径痛感”的价值，但不能证明“稳定正收益”。

## CIO 判断

当前不能把 `etf_regime_rotation_v1b_low_turnover` 定义为收益增强策略。

更准确的阶段性判断：

```text
v1b 的 2021-2023 失效部分来自宽基 ETF 弱 regime；
策略在 2022 和 2024 有防守/择时价值；
但它错过 2021、2025、2026 的固定暴露收益，完整周期仍输给 fixed 60% equal-weight 和 fixed 60% 510500；
因此只能进入“回撤控制 thesis 是否值得保留”的 research-only 审查。
```

## 下一步边界

允许继续：

```text
把 thesis 从收益增强改写为“权益 ETF 仓位管理 / 回撤控制”；
计算收益牺牲换来的最大回撤改善、滚动回撤改善、负窗口减少；
设定明确适用场景：熊市/震荡市防守，而非牛市收益增强；
与现金、fixed 60% equal-weight、fixed 60% 单 ETF 继续比较。
```

停止或降级条件：

```text
如果回撤改善不足以补偿收益损失，则停止 v1b 主线；
如果优势只集中在 2022/2024，不能解释适用 regime，则停止 v1b 主线；
不得继续扩大参数搜索来追逐 2020-2026 历史最优。
```

禁止事项：

```text
不得 paper；
不得 live；
不得接 QMT；
不得真钱交易；
不得把 best20 case 作为推荐参数。
```
