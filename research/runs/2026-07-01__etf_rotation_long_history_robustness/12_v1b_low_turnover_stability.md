# 实验 B2 - v1b 低换手邻域稳定性审查

Verdict: `HOLD_FOR_REGIME_STABILITY_REVIEW`

## 目的

验证 `etf_regime_rotation_v1b_low_turnover` 是否只是单个参数点偶然有效，还是在相邻参数区域也能维持研究价值。

本文件是 research-only 证据，不是 paper/live 准入，不是 QMT 接入建议，也不是交易参数推荐。

## Artifact

`artifacts/v1b_low_turnover_stability.json`

复现命令：

```bash
PYTHONPATH="research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab:src:." \
  .venv/bin/python research/runs/2026-07-01__etf_rotation_long_history_robustness/v1b_low_turnover_stability.py
```

固定口径：

```text
universe = 510300.SH, 510500.SH
trend_window = 60
momentum_window = 20
target_exposure_pct = [0.5, 0.6, 0.7]
min_hold_days = [30, 40, 50]
score_buffer = [0.03, 0.05, 0.07]
slippage = 0 bps and 20 bps
execution = session-fixed T close signal -> T+1 open target execution
```

## 总体结果

| 指标 | 结果 |
| --- | ---: |
| 参数邻域 case | 27 |
| 通过硬门槛 case | 15 |
| 通过完整滚动稳定性 case | 0 |
| 最差 20 bps 总收益 | 5.5492% |
| 20 bps 总收益为正的 case | 27 |
| 拒单 | 0 |

硬门槛定义：

```text
0 bps return >= equal-weight fixed 60% return 23.7395%;
0 bps max drawdown no worse than equal-weight fixed 60% max drawdown -28.4041%;
20 bps return > 0;
rejected orders = 0.
```

## 中心参数复核

中心 case `exposure_0_6_hold_40_buffer_0_05` 与实验 B 记录一致：

| 指标 | 结果 |
| --- | ---: |
| 0 bps return | 26.1822% |
| 0 bps max DD | -19.0827% |
| 20 bps return | 12.9798% |
| 20 bps max DD | -23.5427% |
| orders | 93 |
| turnover | 60.7123x |
| average exposure | 37.2802% |

该 case 通过硬门槛，但未通过滚动稳定性审查。

20 bps 年度结果：

| 年份 | Return | Max DD |
| --- | ---: | ---: |
| 2020 | 8.7667% | -7.2639% |
| 2021 | -0.6010% | -10.6256% |
| 2022 | -9.6685% | -12.4024% |
| 2023 | -6.6066% | -10.0689% |
| 2024 | 13.7548% | -7.9505% |
| 2025 | 2.0497% | -10.6694% |
| 2026 | 4.3637% | -6.1059% |

504 交易日滚动窗口：

| 指标 | 结果 |
| --- | ---: |
| windows | 1068 |
| min return | -21.7476% |
| median return | -1.1376% |
| max return | 26.5224% |
| negative return windows | 568 |

## 最佳 20 bps case

最佳 20 bps 总收益 case 为 `exposure_0_7_hold_30_buffer_0_07`：

| 指标 | 结果 |
| --- | ---: |
| 0 bps return | 32.8948% |
| 0 bps max DD | -20.4959% |
| 20 bps return | 16.7671% |
| 20 bps max DD | -25.5298% |
| orders | 93 |
| turnover | 72.4359x |
| average exposure | 43.2969% |

但该 case 同样有 2021、2022、2023 三个 20 bps 负收益年度，504 交易日滚动窗口中有 571 个负收益窗口，不能作为晋级参数。

## 邻域形态

20 bps 总收益的边际均值：

| 维度 | 参数 | 平均 20 bps return | 最低 | 最高 |
| --- | ---: | ---: | ---: | ---: |
| target_exposure_pct | 0.5 | 10.7381% | 5.5492% | 12.4803% |
| target_exposure_pct | 0.6 | 12.6389% | 6.4011% | 14.7695% |
| target_exposure_pct | 0.7 | 14.2383% | 6.9073% | 16.7671% |
| min_hold_days | 30 | 11.5979% | 5.5492% | 16.7671% |
| min_hold_days | 40 | 13.2777% | 10.6650% | 16.7671% |
| min_hold_days | 50 | 12.7397% | 8.6159% | 16.1163% |
| score_buffer | 0.03 | 9.5220% | 5.5492% | 14.0566% |
| score_buffer | 0.05 | 13.5985% | 10.9633% | 16.1163% |
| score_buffer | 0.07 | 14.4948% | 12.0471% | 16.7671% |

解释：

- 低换手方向不是单点偶然，周边 20 bps 总收益没有塌陷。
- 更高 `score_buffer` 与较高暴露在本样本内表现更好，但不能据此追参。
- `min_hold_days=40` 附近略优，但部分 30/40 case 结果相同，说明真实切换间隔中该约束有时并未绑定。

## 稳定性失败点

所有 27 个 case 在 20 bps 下都有 2021、2022、2023 三个负收益年度。

504 交易日滚动窗口：

| 指标 | 邻域范围 |
| --- | ---: |
| negative return windows | 566 至 592 |
| min rolling return | -26.1731% 至 -17.3904% |
| median rolling return | -3.3616% 至 -0.8391% |

这说明长期总收益为正主要依赖 2020、2024 和 2026 路径修复；中段样本存在持续失效，不能把 v1b 视为完整策略。

## CIO 判断

`etf_regime_rotation_v1b_low_turnover` 继续保留 research-only 研究资格，但不进入 paper。

结论不是“找到可交易参数”，而是：

```text
低换手 ETF 轮动在 2020-2026 全样本和 20 bps 成本压力下没有整体塌陷；
但 2021-2023 的连续负年度与大量负滚动窗口显示 regime 稳定性不足；
下一步必须解释或证伪中段失效，而不是扩大参数搜索。
```

## 下一步边界

允许继续的研究：

```text
对 2021-2023 失效段做 regime 归因；
与 fixed 60% equal-weight、fixed 60% 510300、fixed 60% 510500 做年度和滚动对照；
检查该方向是否应重定义为权益仓位管理工具，而不是收益增强 alpha。
```

禁止事项：

```text
不得 paper；
不得 live；
不得接 QMT；
不得真钱交易；
不得把最佳 20 bps case 当成推荐参数；
不得继续扩大参数网格做历史窗口最优追逐。
```
