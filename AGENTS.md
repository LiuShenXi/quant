﻿# 量化智能体宪法

这个仓库是个人量化平台。任何时候，资金安全、可审计、可复现，都高于速度、优雅程度和策略兴奋感。

## 当前系统边界

- 当前仓库默认不包含真实券商网关、真钱交易、分钟级行情和 Web 管理界面。除非之后有明确评审过的计划，否则不要越过这个边界。
- M3 阶段只允许 Paper trading。M4、QMT、券商接入、真钱相关工作，在 M3b 门禁完成前一律阻塞。
- M3b 必须满足：10 个已计数交易日、每日对账零差异、完成一次断连演练、CRIT 告警送达已验证、没有未解决的人工干预。
- 在任何 M4a/QMT 工作开始前，必须先验证由操作者填写的签核包：

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

只有验证输出包含 `M4a may start`，才表示可以进入下一步工程评审。即便如此，也不代表批准真钱交易。

## 必须使用的 Skills

当任务匹配范围时，必须使用 `.agents/skills` 里的仓库级 skills：

- `strategy-thesis-tracker`：策略想法、alpha 假设、ETF 轮动规则、信号 thesis、策略失效条件。
- `data-audit-reviewer`：行情数据、K 线、交易日历、标的表、复权因子、数据源质量、数据集是否可用。
- `backtest-validator`：回测报告、订单、成交、权益曲线、配置快照、是否可以进入 paper 的审查。
- `risk-governor`：风控限制、仓位规模、回撤控制、订单草案、kill switch、风险准入。
- `paper-live-gatekeeper`：M3b 签核、M4/QMT/券商接入，以及任何接近真钱交易的阶段切换。
- `quant-cio-orchestrator`：从零到一构建量化策略体系、主动找策略、持续优化策略、让 quant loop 跑起来、生成 AI 投委会/CIO 决策包。

如果一个任务同时涉及多个范围，先使用最严格、最接近资金风险的 skill。总监/调度类任务先用 `quant-cio-orchestrator` 分类，再交给对应子 skill 审查。

智能体岗位体系见 `docs/agents/quant-agent-operating-model.md`；Quant CIO 总监模型见 `docs/agents/quant-cio-agent.md`；策略晋级工作流见 `docs/agents/workflow-strategy-promotion.md`；风险授权 hooks 见 `docs/agents/risk-authorization-hooks.md`。

## 不可谈判的规则

1. 回测赚钱，永远不能直接证明可以实盘。
2. 策略从想法进入 paper 前，必须经过 thesis、数据、回测、风控审查。
3. 策略从 paper 走向 M4/QMT/live 前，必须经过 `paper-live-gatekeeper`。
4. 策略不得绕过 `quant.risk`，也不得直接调用 broker/live gateway。
5. 风控必须独立于策略逻辑之外，并且可单独审查。
6. 真实凭证、账号、token、本地 live overlay，不能提交到 git。
7. 不得为了让策略看起来更好，而削弱已有门禁、golden tests、事件持久化、对账或告警。
8. 如果证据缺失，就明确说证据缺失。不能从“没看到问题”推断“安全”。

## 策略晋级流程

任何新策略或策略修改，都按这个顺序推进：

```text
idea 策略想法
-> strategy-thesis-tracker 策略假设记录
-> data-audit-reviewer 数据审查
-> backtest-validator 回测可信度审查
-> risk-governor 风控审查
-> paper observation 纸面观察
-> paper-live-gatekeeper paper/live 门禁
-> human decision 人类决策
```

除非用户明确说明只是做 research-only 讨论，否则跳过任一步都视为审查失败。

## 工程规则

- 保持现有 modular monolith 边界：`core`、`data`、`backtest`、`risk`、`live`、`strategies`。
- 策略代码只能依赖策略契约和白名单第三方库。策略不得 import `data`、`backtest`、`live`、`risk`、`ops`。
- 策略里的时间必须来自 `ctx.now`，不得用真实系统时间做策略决策。
- 每一笔订单、成交、拒单、风控动作、状态变化，都必须能通过持久化事件审计。
- 硬性检查优先用确定性脚本/测试；需要判断的审查再用 skills。
- 做 agent、skill、策略或 gate 相关工作时，不要顺手重构无关模块，除非该改动是完成当前任务所必需的。

## 回答纪律

- 研究问题要分清：假设、证据、假定、证伪条件。
- 晋级或准入问题，要按相关 skill 的要求给明确结论，例如 `PASS`、`PASS_WITH_WARNINGS`、`FAIL`、`REJECT`、`M4_BLOCKED`、`NEEDS_MORE_PAPER`。
- 涉及 live、QMT、券商、真钱的问题，先说阻塞项和所需证据，再谈实现。
- 永远不要把 AI 输出表述成投资建议、投资推荐或交易许可。
