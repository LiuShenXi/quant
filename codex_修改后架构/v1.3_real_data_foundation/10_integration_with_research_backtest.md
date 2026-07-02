# 10 · 与 Research / Backtest / Strategy Contract 集成

## 1. 集成目标

v1.3 数据底座服务策略引擎,但不改变策略契约边界。

原则:

- 策略只依赖 `quant.core.contract` 和白名单第三方库。
- 策略不得 import `quant.data`、`quant.data_providers`、`backtest`、`live`、`risk`。
- Backtest/research 可以通过 `quant.data` reader 消费 curated dataset。
- Provider adapter 不暴露给策略。
- Research report 必须引用 dataset evidence。

## 2. DataService 角色

`DataService` 是上层唯一数据入口。v1.3 应扩展其输入数据来源,而不是让策略直接找 data lake 文件。

建议能力:

- 根据 dataset id 读取 manifest。
- 拒绝读取 `blocked` dataset。
- 对 `curated_candidate` 默认拒绝 backtest claim,除非命令显式声明 audit-only。
- 对 `research_ready` 提供 bars/history/instruments/calendar。
- 暴露 latest_bar_time。
- 保留 legacy fixture 兼容。

## 3. Backtest integration

每次 backtest artifact 应记录:

- dataset id。
- manifest path。
- manifest hash。
- quality verdict。
- audit verdict。
- data coverage。
- decision time policy。
- adjustment policy。

Backtest CLI 在使用 v1.3 dataset 时应拒绝:

- lifecycle `blocked`。
- lifecycle below `research_ready`,除非 research-only dry run。
- quality `FAIL`。
- missing manifest。
- unknown provider。

## 4. Research integration

Research packages 应引用:

- data requirements。
- dataset id。
- audit artifact path。
- known limitations。
- missing fields。
- accepted warnings。

研究报告不得只写“使用真实数据”。必须说明数据来源、区间、口径和 audit verdict。

## 5. CIO package integration

CIO 决策包中的 evidence reviewed 应包含:

- provider field matrix。
- quality report。
- data audit verdict。
- manifest hash。
- dataset limitations。

若数据证据缺失,CIO 默认动作是保持 research-only 或 blocked。

## 6. Strategy promotion impact

策略晋级仍按仓库流程:

```text
idea
-> thesis
-> data audit
-> backtest validation
-> risk review
-> paper observation
-> paper/live gate
-> human decision
```

v1.3 只增强 data audit 之前和 data audit 本身的证据质量。它不跳过 backtest/risk/paper/live gate。

## 7. Import boundaries

推荐边界:

```text
strategies/ -> quant.core.contract only
quant.backtest -> quant.data allowed
quant.data -> quant.core.contract allowed for Bar/Instrument only
quant.data_providers -> no strategy/backtest imports
quant.core -> no data/backtest/live/risk imports
research/ -> may import platform modules
```

若新增 `quant.data_providers`,import-linter 或等价测试应确保 strategies 不可见。

## 8. Compatibility

现有 `data_sample/` 和 tests 应继续可运行。v1.3 实施可新增 richer manifest,但不应迫使所有旧 fixture 一次性迁移。

推荐兼容策略:

- legacy dataset: test fixture only。
- v1.3 dataset: manifest lifecycle enforced。
- bridge reader: old files can be read,但不能自动获得 `research_ready` 语义。

## 9. 报告用语

允许:

- “dataset is research-ready for the documented intended use after data audit PASS.”
- “dataset remains curated_candidate pending audit.”
- “field unavailable; dependent research is blocked.”

禁止:

- “live-ready data。”
- “可以实盘。”
- “真实数据验证通过所以策略可以交易。”
- “回测盈利证明数据和策略可用。”

