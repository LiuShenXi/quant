# ETF v1 退休后的研究队列

Decision: `SET_POST_ETF_V1_RESEARCH_QUEUE`

## 背景

`etf_regime_rotation_v1` 与 `etf_regime_rotation_v1b_low_turnover` 已完成证伪和家族退休。

当前不能继续从 v1/v1b 参数外推，也不能把低换手、score buffer、路径平滑窗口等结果作为新策略起点。

本文件是 research-only CIO 队列整理，不是投资建议，不是交易许可，不是 paper/live/QMT/真钱授权。

## 当前策略状态

| 方向 | 状态 | CIO 判断 |
| --- | --- | --- |
| ETF rotation v1 family | `RETIRE_ETF_ROTATION_V1_FAMILY` | 已退休，仅保留研究素材和引擎修复证据 |
| DualMA 510300 | `OPERATIONAL_BASELINE_ONLY` | 可继续作为 paper/系统验证基线，不作为 alpha 主线 |
| DualMA 510500 | `CANDIDATE_POOL_ONLY` | 有历史 artifact，但 thesis 弱，暂不优先 |
| Crypto Trend Breadth Top2 | `DESIGN_ONLY_CANDIDATE` | 可进入数据与框架准入审查，但不能回测声称或 paper |
| Broader ETF basket | `DEFER_UNTIL_DATA_GOVERNANCE` | 需要先定义多 ETF 数据治理和幸存者偏差处理 |

## 下一优先级

### Priority 1: Crypto Trend Breadth Top2 准入审查

策略 ID:

```text
crypto_trend_breadth_top2_v1
```

来源设计:

```text
docs/superpowers/specs/2026-07-01-crypto-trend-breadth-top2-design.md
```

当前状态:

```text
research-only design;
no dataset;
no data audit;
no backtest artifact;
no paper/live gate.
```

允许动作:

```text
建立正式 research run；
做数据源选择与数据审计设计；
检查当前量化框架是否支持 7x24、4h bars、crypto spot、stablecoin cash state；
只写 thesis/data audit/framework gap，不生成交易信号或订单。
```

禁止动作:

```text
不得 paper；
不得 live；
不得接交易所；
不得真钱；
不得把 CNY 50,000 -> CNY 200,000 当成收益承诺；
不得在缺少数据审计时运行绩效声称。
```

准入硬门槛:

```text
明确数据源、交易所、quote currency、时区、bar close 语义；
可检测 7x24 缺失 bar、重复 bar、stale bar；
可表达 10/20/50 bps 成本压力；
可与 BTC、ETH、SOL、equal-weight、cash、无 breadth/无 stop 版本比较；
回测引擎不得硬编码 crypto 或该策略专属逻辑。
```

### Priority 2: DualMA 510300 运维基线整理

策略 ID:

```text
dual_ma_510300
```

当前状态:

```text
operational baseline;
paper infrastructure validation material;
not alpha thesis.
```

允许动作:

```text
整理 paper observation 与 M3b 证据缺口；
作为引擎、OMS、风控、报告链路的可解释基线；
不把收益表现作为策略晋级依据。
```

禁止动作:

```text
不得把 DualMA 直接升为 alpha 候选；
不得绕过 thesis/data/backtest/risk gate；
不得用系统验证通过替代策略有效性证据。
```

### Priority 3: Broader ETF basket 数据治理

当前状态:

```text
idea only;
no governed universe;
no survivorship controls;
no liquidity/capacity filter.
```

允许动作:

```text
设计 ETF universe governance；
定义上市/退市、停牌、成交额、规模、行业/资产类别标签；
先做数据审计模板，不做策略回测。
```

禁止动作:

```text
不得扩大 ETF 池直接重跑 v1/v1b；
不得用更大标的池掩盖原始 thesis 失败；
不得追历史最优组合。
```

## CIO 路由建议

下一条主线应从 `crypto_trend_breadth_top2_v1` 的正式准入审查开始，但只限于 thesis、数据和框架能力检查。

推荐下一个 research run:

```text
research/runs/YYYY-MM-DD__crypto_trend_breadth_top2_admission_review
```

第一批文件:

```text
00_brief.md
01_thesis_review.md
02_data_source_and_audit_plan.md
03_framework_gap_review.md
04_cio_admission_decision.md
```

## 默认安全动作

```text
research_only = true
paper_gate = FAIL until formal evidence exists
live_gate = FAIL
qmt_gate = FAIL
real_money_gate = FAIL
```

如果任何准入审查中发现量化引擎 bug，应暂停研究，切换工程修复模式，修复并验证后再回到 CIO 研究。
