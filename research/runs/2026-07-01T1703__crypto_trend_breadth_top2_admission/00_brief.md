# 研究简报 - Crypto Trend Breadth Top2 准入研究

Run ID: `2026-07-01T1703__crypto_trend_breadth_top2_admission`
创建时间: 2026-07-01 17:03 +08:00
状态: research-only
策略 ID: `crypto_trend_breadth_top2_v1`

## 目标

基于已落地的业务规格文档，启动 `crypto_trend_breadth_top2_v1` 的准入研究。

本研究包只回答三个问题：

1. 策略 thesis 是否清楚、可证伪，并值得进入数据准备。
2. 数据源、数据质量要求和实验矩阵是否足够明确。
3. 在通用引擎能力补齐前，哪些研究可以继续，哪些结论必须阻塞。

本文档不是投资建议、投资推荐、交易许可、paper 准入、live 准入、交易所接入或真钱授权。

## 策略业务摘要

`crypto_trend_breadth_top2_v1` 是加密现货进攻型 research-only 策略候选：

- 资产范围：BTC spot、ETH spot、SOL spot、stablecoin cash。
- 默认时区：UTC。
- 方向层：日线趋势广度。
- 执行层：4小时强弱排序。
- 风险开启：BTC/ETH/SOL 至少 2 个处于日线上升趋势。
- 持仓：风险开启时持 Top2，默认 60% / 40%。
- 风险关闭：100% stablecoin cash。
- 组合止损：从 active risk cycle peak 回撤 20% 后退现金。
- 冷静期：120 小时，并且趋势广度恢复后才允许重新进场。
- 研究红线：任何正式回测/压力测试最大回撤穿透 35%，不得晋级。

业务规格来源：

- `docs/superpowers/specs/2026-07-01-crypto-trend-breadth-top2-design.md`

## 当前结论

CIO Decision: `CONTINUE_RESEARCH_ONLY_ADMISSION`

可以继续业务研究，但不能生成正式可审查回测结论。原因是当前仓库已有日线、多标的、订单、成交、权益、事件和风控基础，但 crypto v1 需要的 7x24、4小时、多时间框架、quote-currency accounting、bps fee/slippage 和组合级再入场风控仍需由通用引擎能力支持。

## 本研究包产物

- `00_brief.md`：本简报。
- `01_thesis.md`：策略 thesis。
- `02_data_source_screen.md`：数据源候选和数据审查要求。
- `03_experiment_design.md`：实验矩阵和通过/证伪条件。
- `04_risk_review.md`：research-only 风险审查。
- `05_framework_gate.md`：现有引擎能力与阻塞项。
- `06_cio_decision_package.md`：CIO 决策包。

## 默认安全动作

保持 research-only。不得 paper、live、QMT、接交易所、接券商、接真钱、使用真实凭证、生成真实订单或扩大资金边界。

