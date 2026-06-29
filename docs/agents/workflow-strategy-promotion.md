# 策略晋级工作流

本文定义一个策略从想法到下一阶段评审的标准路径。它是流程文档，不创建后台 agent，不接 MCP，不自动交易，也不改变任何运行时代码。

本流程必须遵守根目录 `AGENTS.md` 和 `docs/agents/quant-agent-operating-model.md`。任何 AI 输出都不能表述成投资建议、投资推荐或交易许可。回测赚钱不能直接证明可以实盘。

策略构建、策略优化、策略晋级、风险授权或事故处理请求，默认先由 `Quant CIO Agent` 分类和调度；如果用户明确只要求审查数据、回测、风控或 M3b 签核，则直接进入对应子 agent。

## 总览

```text
阶段 0：策略想法
-> 阶段 1：Strategy Thesis
-> 阶段 2：Data Audit
-> 阶段 3：Backtest Validation
-> 阶段 4：Risk Review
-> 阶段 5：Paper Observation
-> 阶段 6：Paper/Live Gate
-> 阶段 7：Human Decision
```

除非用户明确说明只是 `research-only` 讨论，否则任何策略晋级都必须按顺序经过这些阶段。跳过阶段视为审查失败。

## 阶段 0：策略想法

**目的**

- 把模糊想法收敛成一个可以记录、可以反驳、可以验证的策略候选。

**入口条件**

- 用户提出策略想法、市场观察、ETF 轮动规则、信号想法或 alpha 假设。
- 该想法尚未要求进入 paper、M4、QMT 或真钱阶段。

**负责 agent**

- `Strategy Research Agent`

**必须调用的 skill**

- `strategy-thesis-tracker`

**需要的证据**

- 用户描述的市场现象。
- 已有研究记录、策略草稿、历史回测摘要或相关配置。

**输出结论**

```text
Status: THESIS_DRAFT | THESIS_UPDATE | NEEDS_EVIDENCE | REJECT_THESIS
```

**通过条件**

- 已写清楚策略假设。
- 已列出证据、假设、未知项和证伪条件。
- 已说明下一步需要哪些数据或验证。

**阻塞条件**

- 假设无法证伪。
- 关键证据完全缺失。
- 用户要求直接 paper/live，而 thesis 还没有形成。

**下一步**

- `THESIS_DRAFT` 或 `THESIS_UPDATE`：进入阶段 1。
- `NEEDS_EVIDENCE`：补充研究材料后重试。
- `REJECT_THESIS`：停止晋级。

## 阶段 1：Strategy Thesis

**目的**

- 形成一个可长期追踪的策略 thesis，明确策略为什么可能有效，以及什么情况会证明它无效。

**入口条件**

- 阶段 0 输出 `THESIS_DRAFT` 或 `THESIS_UPDATE`。
- 策略目标、资产范围、频率和大致持有周期已能描述。

**负责 agent**

- `Strategy Research Agent`

**必须调用的 skill**

- `strategy-thesis-tracker`

**需要的证据**

- 策略假设。
- 资产范围。
- 预期信号、规则或 regime 条件。
- 初步证据和相反证据。

**输出结论**

```text
Status: THESIS_DRAFT | THESIS_UPDATE | NEEDS_EVIDENCE | REJECT_THESIS
```

**通过条件**

- thesis 中包含 hypothesis、evidence、assumptions、falsifiers、data needed、validation path。
- 明确该策略仍处于研究阶段，不允许交易。

**阻塞条件**

- 没有证伪条件。
- 只有“感觉会涨”或“回测看起来好”。
- 目标资产、数据频率或持有周期不清楚。

**下一步**

- 进入阶段 2：Data Audit。

## 阶段 2：Data Audit

**目的**

- 判断策略所需数据是否足够可信，能否用于研究或回测。

**入口条件**

- 已有明确 thesis。
- 已知道需要哪些行情、交易日历、标的表、复权因子或其他数据。

**负责 agent**

- `Data Audit Agent`

**必须调用的 skill**

- `data-audit-reviewer`

**需要的证据**

- 数据路径或数据构建记录。
- `bars_1d.csv`、`trade_calendar.csv`、`instruments.csv`、`adjust_factors.csv` 或等价数据。
- 数据源、时间范围、交易日历和复权口径。

**输出结论**

```text
Verdict: PASS | PASS_WITH_WARNINGS | FAIL
```

**通过条件**

- 数据源明确。
- 交易日历、标的表和复权因子与策略需求一致。
- 未发现未来函数、重复、缺失或无法解释的异常。
- 如有 warning，已说明对回测结论的影响。

**阻塞条件**

- 数据源不明。
- 缺少交易日历或复权口径。
- 存在未来数据、幸存者偏差或无法解释的数据修复。
- 数据质量问题会影响策略结论。

**下一步**

- `PASS` 或可接受的 `PASS_WITH_WARNINGS`：进入阶段 3。
- `FAIL`：修复数据后重试，不得进入回测可信度审查。

## 阶段 3：Backtest Validation

**目的**

- 判断回测 artifact 是否可信，是否足以支持进入 paper 讨论。

**入口条件**

- Data Audit 已通过或 warning 已被记录并接受。
- 已有回测配置、数据范围和 artifact 目录。

**负责 agent**

- `Backtest Review Agent`

**必须调用的 skill**

- `backtest-validator`

**需要的证据**

- `orders.csv`
- `trades.csv`
- `equity.csv`
- `events.jsonl`
- `report.md`
- `config_snapshot.yaml`
- 成本、滑点、撮合、T+1 或市场机制假设。

**输出结论**

```text
Verdict: PASS | PASS_WITH_WARNINGS | FAIL
```

**通过条件**

- artifact 齐全且可读取。
- 回测能追溯到明确配置和数据集。
- 成本、滑点和撮合假设不是零成本幻想。
- 没有明显未来函数、模式分支或策略绕过契约。
- 已说明过拟合、参数敏感性、交易次数和样本外风险。

**阻塞条件**

- artifact 缺失或无法复现。
- 成本、滑点或撮合规则不清楚。
- 回测收益依赖少数交易或单一 regime。
- 用户要求从回测直接 live。

**下一步**

- `PASS` 或可接受的 `PASS_WITH_WARNINGS`：进入阶段 4。
- `FAIL`：修复回测或回到阶段 1/2。

## 阶段 4：Risk Review

**目的**

- 判断策略、配置或订单草案是否符合风险边界，是否允许进入 paper 观察。

**入口条件**

- Backtest Validation 已通过。
- 已有策略配置、资金假设、标的范围和风险参数。

**负责 agent**

- `Risk Governor Agent`

**必须调用的 skill**

- `risk-governor`

**需要的证据**

- 策略 YAML。
- `config/risk/` 相关配置。
- 资金规模、单笔订单上限、单标的暴露、回撤限制、loss limit、kill switch。
- 是否存在策略绕过 `quant.risk` 或 broker/live gateway 的路径。

**输出结论**

```text
Decision: APPROVE_FOR_REVIEW | APPROVE_WITH_LIMITS | REJECT
```

**通过条件**

- 风控独立于策略逻辑。
- 策略无法绕过 `quant.risk`。
- 仓位、回撤、单笔订单、单标的暴露和 kill switch 有明确限制。
- 进入 paper 的资金和风险边界已被记录。

**阻塞条件**

- 风控只写在策略内部。
- 策略能直接调用 live/broker gateway。
- 资金规模或风险限制不清楚。
- 对账、告警或事件持久化存在未解决问题。

**下一步**

- `APPROVE_FOR_REVIEW` 或 `APPROVE_WITH_LIMITS`：进入阶段 5。
- `REJECT`：修复风险配置或回到阶段 1/3。

## 阶段 5：Paper Observation

**目的**

- 用 paper 运行观察策略和系统行为，验证对账、事件流水、告警和人工干预流程。

**入口条件**

- Risk Review 已允许进入 paper。
- 已明确 paper 配置、策略配置、事件路径和观察窗口。

**负责 agent**

- `Risk Governor Agent`
- `Ops Incident Agent`

**必须调用的 skill**

- `risk-governor`

如 paper 观察中出现 gate 相关问题，再调用：

- `paper-live-gatekeeper`

**需要的证据**

- paper 事件流水。
- paper 元数据库或对账记录。
- 每日运行记录。
- 告警记录。
- 人工干预记录。

**输出结论**

```text
Paper status: CONTINUE_OBSERVATION | NEEDS_FIX | READY_FOR_M3B_SIGNOFF_REVIEW
```

**通过条件**

- paper 观察未发现未解决异常。
- 对账差异为零。
- 事件流水可审计。
- 告警链路可验证。
- 若准备进入 M3b 签核，必须满足 10 个已计数交易日、断连演练和 CRIT 告警送达验证要求。

**阻塞条件**

- 任一交易日存在未解决对账差异。
- 事件流水缺失或无法重放。
- 出现未解决人工干预。
- CRIT 告警链路未验证。
- 断连演练缺失。

**下一步**

- `CONTINUE_OBSERVATION`：继续 paper。
- `NEEDS_FIX`：修复后重新观察，必要时重新计数。
- `READY_FOR_M3B_SIGNOFF_REVIEW`：进入阶段 6。

## 阶段 6：Paper/Live Gate

**目的**

- 判断 M3b 签核是否满足进入 M4a/QMT 工程评审的前置条件。

**入口条件**

- Paper Observation 已达到 `READY_FOR_M3B_SIGNOFF_REVIEW`。
- 已有操作者填写的 `m3b_signoff.yaml`。

**负责 agent**

- `Paper/Live Gatekeeper Agent`

**必须调用的 skill**

- `paper-live-gatekeeper`

**需要的证据**

- `m3b_signoff.yaml`
- paper `events.jsonl`
- 交易日历
- 10 个已计数交易日
- 每日对账零差异
- 断连演练记录
- CRIT 告警送达记录
- 无未解决人工干预

**必须运行的命令**

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

**输出结论**

```text
Decision: M4_BLOCKED | M4A_MAY_START_FOR_HUMAN_REVIEW | NEEDS_MORE_PAPER
```

**通过条件**

- 验证命令成功。
- 输出包含 `M4a may start`。
- 证据与签核包一致。

**阻塞条件**

- 签核包缺失。
- 验证命令失败。
- 少于 10 个已计数交易日。
- 任一天对账非零差异。
- 断连演练或 CRIT 告警送达缺失。
- 存在未解决人工干预。

**下一步**

- `M4A_MAY_START_FOR_HUMAN_REVIEW`：进入阶段 7。
- `M4_BLOCKED` 或 `NEEDS_MORE_PAPER`：保持 M4/QMT/live 阻塞。

## 阶段 7：Human Decision

**目的**

- 由人类决定是否开始下一步工程工作。AI 只能整理证据和阻塞项，不能批准真钱交易。

**入口条件**

- Paper/Live Gate 输出 `M4A_MAY_START_FOR_HUMAN_REVIEW`。
- 所有阻塞项已关闭或明确接受。

**负责 agent**

- `Paper/Live Gatekeeper Agent`
- 必要时联合 `Risk Governor Agent` 和 `Ops Incident Agent`

**必须调用的 skill**

- `paper-live-gatekeeper`
- 如涉及风险变更，再调用 `risk-governor`

**需要的证据**

- M3b 签核验证输出。
- 风控审查结论。
- paper 观察摘要。
- 人类操作者的最终确认。

**输出结论**

```text
Human decision required: APPROVE_ENGINEERING_NEXT_STEP | HOLD | REJECT
```

**通过条件**

- 人类明确批准下一步工程评审或开发。
- 批准范围只限下一步工程，不等于真钱交易许可。

**阻塞条件**

- 人类没有明确确认。
- 批准范围不清楚。
- 仍有未关闭事故、风险或证据缺口。

**下一步**

- `APPROVE_ENGINEERING_NEXT_STEP`：可以为下一步工程写计划。
- `HOLD`：保持当前阶段。
- `REJECT`：停止晋级，回到相应修复阶段。

## 全局停止规则

出现以下任一情况，立即停止晋级：

- 用户要求因为回测赚钱而跳过 paper。
- 用户要求绕过 `paper-live-gatekeeper`。
- 策略试图绕过 `quant.risk` 或直接调用 broker/live gateway。
- 真实凭证、账号、token 或本地 live overlay 将被提交到 git。
- 事件流水、对账、告警、风控或签核证据缺失。
- AI 被要求代替人类批准交易。

停止后，输出必须包含：

```text
Stop reason:
Missing evidence:
Required fix:
Allowed next step:
```
