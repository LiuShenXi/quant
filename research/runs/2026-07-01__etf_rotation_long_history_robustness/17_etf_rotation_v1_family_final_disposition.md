# ETF 轮动 v1 家族最终处置

Decision: `RETIRE_ETF_ROTATION_V1_FAMILY`

## 范围

本处置覆盖：

```text
etf_regime_rotation_v1
etf_regime_rotation_v1b_low_turnover
```

标的范围：

```text
510300.SH
510500.SH
```

本文件是 research-only CIO 处置，不是投资建议、交易许可、paper/live 准入或 QMT 接入授权。

## 最终结论

ETF 轮动 v1 家族不再作为候选策略推进。

处置：

```text
paper_gate = FAIL
live_gate = FAIL
qmt_gate = FAIL
real_money_gate = FAIL
strategy_family_status = RETIRE_ETF_ROTATION_V1_FAMILY
```

允许保留：

```text
历史研究素材；
引擎修复回归证据；
未来 ETF 仓位管理研究的反例约束。
```

禁止继续：

```text
不得继续扩大 v1/v1b 参数搜索；
不得把 v1b center 或 best20 作为推荐参数；
不得从 v1/v1b 直接生成 paper observation plan；
不得接 QMT；
不得真钱交易。
```

## 证伪链条

### 1. 原始 v1 退场

session-fixed 真实执行口径下：

| 指标 | 结果 |
| --- | ---: |
| v1 return | 18.4487% |
| v1 max DD | -29.4192% |
| 510300 buy-and-hold return | 20.9689% |
| 510500 buy-and-hold return | 58.1627% |
| equal-weight hold return | 39.5658% |
| 20 bps slippage return | -8.3175% |

结论：

```text
原始 v1 收益增强 thesis 不成立；
20 bps 成本压力下收益为负；
执行时点路径依赖严重；
原始 v1 降级为研究素材。
```

### 2. 风险关闭基准失败

实验 A 显示：

| 指标 | 结果 |
| --- | ---: |
| v1 baseline return | 18.4487% |
| v1 baseline max DD | -29.4192% |
| fixed 60% equal-weight return | 23.7395% |
| fixed 60% equal-weight max DD | -28.4041% |
| average exposure | 45.4080% |
| days exposure below 5% | 43.4755% |
| turnover / initial cash | 133.7814x |

结论：

```text
v1 没有战胜更简单的固定 60% 等权暴露；
低回撤不能归因于稳定有效择时；
高换手没有得到足够收益补偿。
```

### 3. v1b 低换手变体只短暂保留研究资格

实验 B 找到低换手候选：

```text
target_exposure_pct = 0.6
min_hold_days = 40
score_buffer = 0.05
```

该中心 case：

| 指标 | 结果 |
| --- | ---: |
| 0 bps return | 26.1822% |
| 0 bps max DD | -19.0827% |
| 20 bps return | 12.9798% |
| 20 bps max DD | -23.5427% |
| orders | 93 |
| turnover | 60.7123x |

结论：

```text
v1b 不是单点立即塌陷；
但只能作为 research-only 假设继续证伪；
不能进入 paper。
```

### 4. 参数邻域和滚动稳定性不足

实验 B2：

| 指标 | 结果 |
| --- | ---: |
| 参数邻域 case | 27 |
| 通过硬门槛 case | 15 |
| 20 bps 总收益为正 case | 27 |
| 通过完整滚动稳定性 case | 0 |

关键问题：

```text
所有 case 在 20 bps 下 2021、2022、2023 均为负收益年度；
504 日滚动窗口中大量窗口为负；
长期总收益为正不能替代路径稳定性。
```

### 5. 收益增强 thesis 不成立

实验 B3：

| Portfolio | Return | Max DD |
| --- | ---: | ---: |
| v1b center 20 bps | 12.9798% | -23.5427% |
| v1b best20 20 bps | 16.7671% | -25.5298% |
| fixed 60% equal-weight | 23.7395% | -28.4041% |
| fixed 60% 510500 | 34.8976% | -32.5967% |

结论：

```text
v1b 全周期收益低于 fixed 60% equal-weight 和 fixed 60% 510500；
不能定义为收益增强 alpha。
```

### 6. 回撤控制 thesis 被简单固定暴露削弱

实验 B5：

| Portfolio | Return | Max DD | 504d Negative Windows |
| --- | ---: | ---: | ---: |
| v1b center | 12.9798% | -23.5427% | 568 |
| fixed 40% equal-weight | 15.8263% | -20.0967% | 658 |
| v1b best20 | 16.7671% | -25.5298% | 571 |
| fixed 50% equal-weight | 19.7829% | -24.3739% | 658 |

结论：

```text
fixed 40% equal-weight 同时优于 v1b center 的收益和最大回撤；
fixed 50% equal-weight 同时优于 v1b best20 的收益和最大回撤；
v1b 不能证明更好的收益-最大回撤效率。
```

### 7. 路径平滑 thesis 不稳定

实验 B6：

相对 fixed 40%/50%/60% equal-weight 的负收益窗口减少数量：

| Strategy | 252 sessions | 504 sessions | 756 sessions |
| --- | ---: | ---: | ---: |
| v1b center | -23 | 90 | -88 |
| v1b best20 | -24 | 87 | -36 |

结论：

```text
路径平滑优势只在 504 日窗口成立；
在 252 和 756 日窗口不成立；
该效用依赖窗口定义，不稳定；
v1b 主线退休。
```

## 引擎修复收获

本研究过程中发现并修复了多项量化引擎问题：

```text
target order sizing 切片；
position_limit 不应拒绝风险降低卖单；
日线多标的 session 时间线；
跨标的错误撮合；
多标的日线统一开盘执行、收盘估值和每日一条 equity。
```

这些修复是本研究的主要工程价值，但不构成策略有效性证据。

## 未来研究约束

如果未来重启 ETF 仓位管理研究，必须作为新主线，不得从 v1/v1b 参数继续外推。

新主线最低要求：

```text
先定义 thesis，再定义参数；
先定义真实执行口径，再跑收益；
必须比较 cash、fixed 40%/50%/60% equal-weight、fixed 40%/50%/60% 单 ETF；
必须报告 252/504/756 多窗口滚动收益、回撤、负窗口数量；
必须纳入 10/20 bps 成本压力；
不得只用单一窗口或单一参数点作为晋级证据；
不得在未通过固定暴露替代审查前讨论 paper。
```

## 最终 CIO 状态

```text
etf_regime_rotation_v1 = DEMOTE_TO_RESEARCH_MATERIAL
etf_regime_rotation_v1b_low_turnover = RETIRE_V1B_MAINLINE
family_status = RETIRE_ETF_ROTATION_V1_FAMILY
next_action = stop v1/v1b research; archive as evidence and constraints
```

本处置不是投资建议，不是交易许可，不是 paper/live/QMT/真钱授权。
