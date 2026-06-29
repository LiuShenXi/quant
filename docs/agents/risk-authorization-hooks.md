# 风险授权 Hooks

本文定义量化智能体系统里的风险授权边界。核心原则：你授权的是风险边界，不是每笔交易。

自动交易在本仓库里的含义是：系统在已授权边界内自动执行规则；越界时自动拒绝、冻结或阻塞；晋级、扩容、事故恢复、风险边界变更、交易行为变更才请求你确认。

## 授权分工

```text
你 = 风险边界授权人 / 资金授权人
Quant CIO Agent = 策略构建、证据整理、改进建议和 hook 触发建议
Risk Governor Agent = 风险边界审查
系统 = 边界内自动执行，边界外默认阻塞
```

你不需要判断每笔订单是否专业，也不需要逐笔批准交易。你需要批准的是策略是否可以进入某个阶段、可使用的资金范围、最大仓位、最大亏损、可交易标的、允许频率、事故恢复条件和是否接受某个风险边界变更。

## Hook 类型

### Strategy approval hook

**触发条件**

- 新策略进入 research/backtest/paper。
- 现有策略从 research-only 变为可验证候选。
- Quant CIO 建议把某个策略加入正式研究路线图。

**要求**

- 必须已有 thesis、数据需求、实验计划、失败条件和晋级路径。
- 进入 paper 前必须完成 thesis、data、backtest、risk 审查。

**默认动作**

- 证据不足时保持 research-only。

### Pre-trade hook

**触发条件**

- 订单草案进入风控检查。

**现有对应**

- `RiskEngine.check_order`

**要求**

- 检查单笔订单、单标的、策略、账户、日亏损和 kill switch。
- 策略不能绕过 `quant.risk`。

**默认动作**

- 风险检查失败则拒单。

### Drawdown hook

**触发条件**

- 日亏损、权益曲线或回撤达到预设阈值。

**现有对应**

- `RiskEngine.on_equity`

**要求**

- 达到 freeze/halt 条件时冻结或停止相关策略。
- 恢复前必须有原因解释、事件证据和风险复核。

**默认动作**

- 达到阈值时 freeze/halt。

### Market-data hook

**触发条件**

- 行情陈旧、缺失、时间戳异常或无法满足策略频率要求。

**现有对应**

- `RuntimeMonitor.check_market_data`

**要求**

- 数据陈旧时不得继续把信号当作可执行依据。
- 需要记录数据源、时间、影响范围和恢复条件。

**默认动作**

- 行情陈旧触发 freeze。

### Gateway incident hook

**触发条件**

- 断连、重连、报单异常、成交异常、对账异常、告警异常或人工干预。

**要求**

- 触发 `Ops Incident Agent` 复盘。
- 必要时调用 `risk-governor` 和 `paper-live-gatekeeper`。
- 事故未关闭前，不得推动 M4/QMT/live-adjacent 晋级。

**默认动作**

- 冻结相关晋级或交易行为，直到事故复盘给出可审计结论。

### Promotion hook

**触发条件**

- paper 到 M4/QMT/live-adjacent 前。

**现有对应**

- `validate_m3b_signoff.py`

**要求**

- 必须运行：

```bash
python scripts/validate_m3b_signoff.py path/to/m3b_signoff.yaml
```

- M3b 必须满足 10 个已计数交易日、每日对账零差异、完成一次断连演练、CRIT 告警送达已验证、没有未解决的人工干预。

**默认动作**

- M3b 未通过时，M4/QMT/真钱相关工作阻塞。

### Capital expansion hook

**触发条件**

- 增加资金。
- 放宽仓位。
- 提高亏损阈值。
- 扩大标的池、频率或风险预算。

**要求**

- 必须由 `Risk Governor Agent` 审查。
- 必须明确旧边界、新边界、证据、预期收益、最坏情形和回滚条件。
- 必须由你人工授权。

**默认动作**

- 未授权前保持旧边界。

### Strategy change hook

**触发条件**

- 策略参数、标的池、信号逻辑、组合权重发生影响交易行为的变化。
- Quant CIO 提出 v1.1/v2，且该调整会改变 paper/live 行为。

**要求**

- 重新经过 thesis、data、backtest、risk 审查。
- live 参数、资金上限或风险边界不能由 AI 直接修改并运行。

**默认动作**

- 未完成重新审查和授权前，保持旧策略或暂停推进。

## 边界规则

- 边界内自动执行：订单、风控检查、freeze/halt、数据陈旧拦截、事件记录按已授权规则运行。
- 边界外默认阻塞：越界请求默认拒绝、冻结或阻塞。
- 晋级需要授权：paper 到 M4/QMT/live-adjacent 必须经过 `Promotion hook`。
- 扩容需要授权：资金、仓位、亏损阈值、风险预算变更必须经过 `Capital expansion hook`。
- 交易行为变更需要授权：参数、标的池、信号逻辑、组合权重影响交易行为时必须经过 `Strategy change hook`。
- 事故恢复需要授权：网关、对账、告警、人工干预等事故未复盘前，不恢复晋级。

## AI 边界

- Quant CIO 可以建议触发 hook，但不能批准真钱交易。
- Risk Governor 可以给风险审查结论，但不能替你批准资金边界扩大。
- Paper/Live Gatekeeper 可以判断 M3b 是否满足下一步工程评审条件，但不能授权真钱交易。
- 如果 hook 证据缺失，默认保持更保守状态。
