# v1.2 Research Engine 架构包

版本: v1.2-research-engine
日期: 2026-07-01
定位: 通用研究引擎增量架构，不是 crypto 专用策略实现
状态: architecture package / research-only engineering design

本包继承 `codex_修改后架构/` 的 v1.1-codex 基线。v1.1 的第一目标是把 A股 ETF 日线可信回测和 Paper 前置基础设施做稳；v1.2 的目标是把平台能力推进到可支持跨市场、多频、7x24、报价币种账户和通用研究报告的研究引擎。

这不是投资建议、投资推荐、paper 批准、live 批准、QMT 批准、交易所接入批准或真钱交易许可。

## Superpowers Trace

- Process: `superpowers:brainstorming` for architecture design, then code-review reception for review findings.
- User-approved scope: first vertical research slice, not all framework tickets at once.
- Current artifact: architecture package only.
- Next gate: user review of this package before implementation planning.
- Not allowed from this package alone: code implementation, paper/live/QMT/exchange/broker/real-money work.

## 版本目标

v1.2 第一轮只做一个垂直切片:

- 可配置市场日历，先支持 A股交易日历和 7x24 连续日历。
- 多频 bar 时间轴，先支持日线状态 + 4h 执行的无未来函数语义。
- 报价币种账户和 fractional spot 记账，不能把 CNY、整手、T+1 写死进框架。
- 目标权重接口，至少支持 `set_target_weight` 进入通用 target-to-order 路径。
- bps fee/slippage 成本模型，作为可复用成本模型而非 crypto 特例。
- 组合级 trailing drawdown stop、cooldown 和 re-entry gate，作为独立可审查风控组件。
- append-only event journal schema，让状态变化、风控动作和回测产物可审计。
- 通用 benchmark/report 产物，支持 JSON + Markdown，并带 research-only disclaimer。

## 文档地图

| 编号 | 文件 | 内容 |
| --- | --- | --- |
| 01 | `01_iteration_scope.md` | 迭代边界、非目标、与 v1.1 的关系 |
| 02 | `02_target_architecture.md` | v1.2 目标架构、模块职责、依赖方向 |
| 03 | `03_data_calendar_multitimeframe.md` | 数据集、日历、bar 频率、多频无未来函数语义 |
| 04 | `04_backtest_execution_accounting.md` | 回测时间轴、target/order/fill、fractional spot 和报价币种账户 |
| 05 | `05_cost_risk_reporting.md` | bps 成本、组合风控、事件、报告和 benchmark |
| 06 | `06_acceptance_slices.md` | 第一轮验收切片和测试证据 |
| 07 | `07_implementation_roadmap.md` | 后续实现顺序、拆分建议和门禁 |

## 设计守则

1. 平台层不得 import 或引用具体策略 ID。
2. 币种、频率、EMA、排名窗口、权重、止损阈值、冷却期和 benchmark 集合必须来自配置或策略层输入。
3. 策略仍只能依赖 `quant.core.contract` 和白名单库，不得 import `data/backtest/live/risk/ops`。
4. 风控必须独立于策略逻辑之外，并能单独测试。
5. 每一笔订单、成交、拒单、风控动作和状态变化都必须能进入事件流水。
6. 第一轮只允许 research/backtest，不接交易所、不接 broker、不生成真钱订单。
