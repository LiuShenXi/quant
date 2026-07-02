# A 股 2026-07-06 交易新规影响清单

Status: `THESIS_DRAFT`

结论：当前本地 A 股 ETF/基金数据与执行模型不足以支持 2026-07-06 后的尾盘、收盘集合竞价、盘后固定价格交易回测。对这类执行模型的本地数据审计结论为 `FAIL`；对既有日线、T 收盘后信号、T+1 开盘执行的研究结论，最多只能给 `PASS_WITH_WARNINGS`，且必须声明日线 volume 口径未能拆分普通竞价、收盘集合竞价和盘后固定价格成交。

本清单不是投资建议，不是 paper/live 准入，也不批准任何真钱交易。

## 扫描范围

- 策略代码：`strategies/dual_ma.py`，`research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/etf_regime_rotation.py`
- 策略/回测配置：`config/strategies/*.yaml`，`research/imported/usage_records/2026-06-26__quant_usage_record/backtest/*.yaml`，`research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/*.yaml`
- 回测执行：`src/quant/backtest/engine.py`，`src/quant/backtest/matcher.py`
- 风控 session：`src/quant/risk/checks.py`，`src/quant/risk/pipeline.py`
- 数据：`data_sample/`，`data_real/`，`research/datasets/`，`research/imported/usage_records/2026-06-26__quant_usage_record/data/`
- Paper runbook：`docs/runbooks/paper_daily_runbook.md`

## 模式扫描结果

| 模式 | 结果 | 证据 | 影响 |
| --- | --- | --- | --- |
| `14:57-15:00` 尾盘成交 | 未发现策略显式用该时间窗成交 | 风控只允许连续竞价到 `14:57`；回测日线撮合在 `09:31` 开盘附近执行 pending target | 未发现直接尾盘成交策略，但 session 模型缺少收盘集合竞价和盘后定价交易 |
| 当日信号用当日 `close` | 发现 | `DualMA` 和 ETF 轮动都用 `ctx.history(..., fields=["close"])`；回测在日线 `15:00` 后调用 `on_bar` | 需要重验 close 语义，尤其沪市基金 2026-07-06 后 close 来自收盘集合竞价 |
| 当日 `close` 信号并假设同日 `close` 成交 | 主引擎未发现 | 日线回测先在开盘 flush pending target，再在收盘后生成新 target；既有研究文档声明 `T close signal -> T+1 open` | 不是同日 close fill，但不能覆盖收盘集合竞价或盘后固定价格交易策略 |
| ETF/基金收盘调仓 | 发现 ETF/基金调仓研究，但不是收盘成交模型 | `dual_ma_510300*`、`dual_ma_510500_record_probe`、`etf_regime_rotation_510300_510500_v1/v1b` 都是 ETF 日线策略 | 受新规影响，需要重新声明 T+1 open、收盘集合竞价、盘后定价三种执行口径 |
| 用日线 volume 估容量/冲击/participation | 发现 | `Matcher(volume_limit_pct=0.05)` 用 `bar.volume` 限制成交量；执行敏感性研究使用 bps slippage | 2026-07-06 后若日线 volume 包含盘后固定价格交易，容量和冲击成本会被高估或口径漂移 |

## 策略影响分类

| 策略/配置 | 分类 | 触发模式 | 结论 |
| --- | --- | --- | --- |
| `config/strategies/dual_ma_510300.yaml` | `impacted` | 沪市 ETF；用当日日线 close 形成 MA 信号；回测容量用日线 volume | 可以继续作为旧式 T 收盘后信号、T+1 开盘执行研究，但 2026-07-06 后必须重验 close/volume 口径 |
| `config/strategies/dual_ma_510300_paper.yaml` | `impacted` | 同上，且连接 paper 流程 | Paper 观察若跨过 2026-07-06，需要新增数据口径说明；不能把 15:00 日线 volume 当作可审计尾盘/盘后容量 |
| `config/strategies/dual_ma_510300_real_validation.yaml` | `impacted` | 沪市 ETF；真实数据验证路径；日线 close 信号 | 2026-07-06 后结果需标注制度断点 |
| `config/strategies/dual_ma_510300_real_validation_paper.yaml` | `impacted` | 当前 M3 paper 验证路径；runbook 15:10 接受当日 15:00 日线 | 跨新规日后应暂停“尾盘/收盘执行模型”结论，只能观察 T+1 open 执行链路 |
| `research/imported/.../backtest/dual_ma_510500_20_60.yaml` | `impacted` | 沪市 ETF `510500.SH`；同一 `DualMA` 类；日线 close 信号 | 需重验 post-rule close/volume 口径 |
| `research/imported/.../strategy_lab/etf_regime_rotation_510300_510500.yaml` | `impacted` | ETF 轮动；日线 close 排名；target qty 用 close 估值；多 ETF 调仓 | 研究族 v1/v1b 的执行敏感性结论需在新规后重跑 |
| `research/runs/2026-07-01__etf_rotation_long_history_robustness/*v1b*` | `impacted` | 复用 ETF 轮动策略；显式研究 slippage、换手、调仓路径 | v1b 仍是 research-only；新规后需单独做 execution-regime split |
| `tests/fixtures/*continuous_24x7*` 与 crypto research fixtures | `not impacted` | 非 A 股、非 ETF/基金、连续 24x7 | 不受本次 A 股 ETF/基金交易机制变化影响 |
| 其他测试夹具与 `data_sample` 示例策略路径 | `unclear` | 多为通用引擎测试或样例，不代表可交易策略 | 若被拿来做 ETF/基金执行研究，必须先补 session/volume 字段 |

## 本地数据审计

Verdict: `FAIL`

Dataset reviewed:

- `data_real/etf_510300_2025_2026_check`
- `data_real/etf_510300_2025_2026_midday_probe`
- `data_real/etf_510500_2025_2026_check`
- `research/datasets/akshare_510300_20200101_20260630`
- `research/datasets/akshare_510500_20200101_20260630`
- `research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630`
- imported 2026-06-26 ETF datasets

Intended use:

- 2026-07-06 后 ETF/基金尾盘交易、收盘集合竞价、盘后固定价格交易执行模型。

Blocking issues:

- 所有本地 A 股 ETF 数据集只有 `bars_1d.csv`，未发现分钟线文件。
- `bars_1d.csv` 字段为 `symbol, dt, open, high, low, close, volume, amount, pre_close, limit_up, limit_down, suspended, data_status, source, updated_at`，没有 `session_phase`、`volume_scope`、`continuous_volume`、`closing_auction_volume`、`after_hours_fixed_price_volume`。
- 数据最大日期为 `2026-06-30T15:00:00+08:00`，早于 2026-07-06 新规生效日，不能用本地样本实证判断新规后日线 volume 是否并入盘后固定价格成交。
- `akshare` 构建器只生成 `bars_1d.csv`、`instruments.csv`、`adjust_factors.csv`、`trade_calendar.csv`，并将 bar 时间标准化到 `15:00`，未保存普通竞价、收盘集合竞价、盘后定价交易的来源拆分。

Warnings:

- `data_real/etf_510300_2025_2026_check` 的 source 为 `akshare:fund_etf_hist_sina+tx_daily+fund_etf_spot_em`，但没有字段说明 `fund_etf_spot_em` 的成交量是否含盘后固定价格交易。
- `research/datasets/*20200101_20260630` 使用 `akshare:fund_etf_hist_em`，但同样没有日线 volume scope。
- Paper runbook 在 15:10 后接受当日 `15:00` 日线 bar，这对“收盘后可用日线”是合理流程检查，但不能证明该 bar 的 volume/session 口径满足 2026-07-06 后执行建模。

Checks performed:

- 枚举本地 `bars_*.csv`：未发现 `bars_1m.csv`、`bars_5m.csv` 或其他分钟级 A 股 ETF 数据。
- 检查所有本地 A 股 ETF `bars_1d.csv` 表头：全部缺少 session/volume 拆分字段。
- 检查数据日期范围：全部为 2026-07-06 以前样本。
- 检查执行模型：日线回测使用 T 日收盘后信号、T+1 开盘撮合；matcher 用 `bar.volume * 0.05` 做成交上限。
- 检查风控 session：当前只认 `09:30-11:30` 与 `13:00-14:57` 连续竞价。

Evidence:

- `strategies/dual_ma.py` 使用 close MA 信号。
- `src/quant/backtest/engine.py` 日线 session 中先开盘 flush pending target，再收盘生成新 target。
- `src/quant/backtest/matcher.py` 用日线 `bar.volume` 做 volume cap。
- `src/quant/risk/checks.py` 只实现连续竞价窗口。
- `src/quant/data/akshare_etf.py` 数据文件集合只包含日线 bar 等四类 CSV，且 `_market_close_iso` 固定 `15:00`。
- `docs/runbooks/paper_daily_runbook.md` 在 `15:10` 后刷新并确认当日 `15:00` 日线 bar。

Required fixes:

1. 在数据契约中新增 session/volume 口径：至少包含 `session_phase` 或独立的 `continuous_volume`、`closing_auction_volume`、`after_hours_fixed_price_volume`。
2. 引入 2026-07-06 后样本，分别核对数据商日线 volume 是否包含盘后固定价格交易。
3. 增加分钟线或分 session 成交数据；若供应商只能给日线，则不得用它验证尾盘/收盘集合竞价/盘后定价执行模型。
4. 将执行模型拆成三类：T+1 open、closing auction、after-hours fixed price；回测报告必须声明使用哪一类。
5. 风控 session 增加收盘集合竞价与盘后固定价格交易的显式规则，且不能绕过 `quant.risk`。
6. 对受影响策略重跑 post-rule execution split：pre-2026-07-06 与 post-2026-07-06 分段报告，至少比较收益、换手、成交容量、拒单、滑点压力和 benchmark。

## 下一步决策

`NEEDS_EVIDENCE`

在补齐 2026-07-06 后带 session 拆分的数据前，不应把任何 ETF/基金尾盘、收盘集合竞价、盘后固定价格交易回测标记为可审查通过。既有 `dual_ma` 和 ETF 轮动研究可以继续作为 T 收盘后信号、T+1 开盘执行的 research-only 材料，但必须在报告里声明：日线 volume 未审明是否含盘后固定价格成交，不能用于 post-rule 尾盘/盘后容量结论。
