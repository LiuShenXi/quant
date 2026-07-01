# 实验 A - 风险关闭与暴露审查

Verdict: `FAIL_RISK_OFF_BASELINE`

## 目的

验证 `etf_regime_rotation_v1` 的低回撤是否来自有效择时，还是主要来自长期空仓/低暴露。

本文件是 research-only 证据，不是 paper/live 准入，也不是交易建议。

## Artifact

`artifacts/risk_off_baseline_exposure_audit.json`

计算口径：

```text
strategy_exposure = (total_value - cash) / total_value
equity_source = session-fixed equity.csv
benchmark = close-to-close normalized fixed exposure + cash
```

## 策略暴露画像

| 指标 | 数值 |
| --- | ---: |
| average exposure | 45.4080% |
| median exposure | 79.5496% |
| max exposure | 84.7177% |
| days exposure below 5% | 683 |
| days exposure below 5% pct | 43.4755% |
| days exposure above 70% | 888 |
| days exposure above 70% pct | 56.5245% |
| trades | 161 |
| total trade notional | 13,378,142.60 |
| turnover / initial cash | 133.7814x |

解释：

策略不是稳定低仓位，而是在“接近空仓”和“接近 80% 暴露”之间切换。它有 43.4755% 的交易日几乎空仓，同时仍产生 133.7814 倍初始资金的累计成交额。

## 固定暴露对照

| Case | Return | Max DD | Annualized Return |
| --- | ---: | ---: | ---: |
| strategy baseline | 18.4487% | -29.4192% | 2.7531% |
| equal-weight fixed 60% | 23.7395% | -28.4041% | 3.4759% |
| equal-weight fixed 80% | 31.6527% | -35.8043% | 4.5099% |
| equal-weight fixed 100% | 39.5658% | -42.4382% | 5.4930% |
| 510300 fixed 60% | 12.5813% | -30.5494% | 1.9191% |

## Gate 结果

实验 A 未通过。

原因：

- 策略 baseline 收益 `18.4487%`，低于 `equal-weight fixed 60%` 的 `23.7395%`。
- 策略最大回撤 `-29.4192%`，也没有优于 `equal-weight fixed 60%` 的 `-28.4041%`。
- 策略承担了高换手和滑点风险，但未超过简单固定 60% 等权暴露。
- 低回撤不能被归因于有效择时；更像是暴露切换没有带来足够补偿。

## CIO 解释

这个结果进一步支持 `DEMOTE_TO_RESEARCH_MATERIAL`。原始 v1 不能作为 paper 候选策略继续推进。

如果继续研究 ETF 轮动方向，应该转向：

```text
更低换手；
更明确的权益仓位管理 thesis；
先战胜固定暴露基准，再讨论轮动 alpha。
```

## 下一步

实验 B 可以继续，但必须严格限定为 research-only：

```text
increase min_hold_days;
increase score_buffer;
reduce target_exposure_pct;
require 20 bps slippage return > 0;
require performance better than equal-weight fixed 60%.
```

若实验 B 仍无法超过固定暴露基准，应停止该 ETF v1 主线。
