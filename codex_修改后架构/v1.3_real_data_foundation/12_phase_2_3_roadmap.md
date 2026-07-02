# 12 · Phase 2 / Phase 3 Roadmap

## 1. 原则

Phase 2 和 Phase 3 是未来路线,不是 Phase 1 当前实现范围。进入这些阶段必须有明确研究需求、Phase 1 稳定证据和新的质量门禁。

默认安全动作:没有证据就不升级复杂度。

## 2. Phase 2: 分钟和更高频数据

候选方向:

- A 股历史分钟数据 from Tushare。
- JQData/RQData trial for minute/tick coverage。
- Crypto minute bars from exchange APIs。
- 更细的 execution-cost and slippage research dataset。

## 3. Phase 2 entry criteria

Phase 2 启动前必须满足:

- Phase 1A/1B daily/4h data contracts 稳定。
- Data lake 能处理当前数据量。
- Quality/audit gates 已有通过样本和失败样本。
- 有策略研究需求证明日线/4h 不够。
- 明确分钟级数据不会被误解为 live execution approval。

## 4. Phase 2 新问题

Phase 2 必须回答:

- 分钟数据完整性是否足够。
- timestamp 是否 session-aligned。
- 半日市、停牌、临停、集合竞价如何表示。
- corporate action adjusted minute semantics 是否可靠。
- 数据体量是否仍适合本地 data lake。
- intraday missing interval 如何检测。
- provider 延迟和修订如何记录。

## 5. Phase 2 禁止事项

- 不自动解锁 same-day board-capture。
- 不自动解锁 high-frequency trading。
- 不自动解锁 live execution。
- 不以 provider 可下载分钟数据作为策略可交易证据。

## 6. Phase 3: 机构和研究级数据源

候选升级:

- CSMAR 或 RESSET: 学术级 fundamentals、delisted securities、高频历史。
- Wind、Choice、iFinD: 专业终端/API 覆盖。
- Kaiko、Coin Metrics、CoinDesk Data: 机构级 crypto history and normalization。

Phase 3 是 procurement and governance upgrade,不是 adapter sprint。

## 7. Phase 3 entry criteria

Phase 3 启动前必须满足:

- Phase 1 data foundation stable。
- 免费或低成本 source 无法满足已记录研究需求。
- vendor comparison report exists。
- cost reviewed。
- license and export rights reviewed。
- credential handling reviewed。
- migration plan exists。

## 8. Vendor comparison report

Vendor comparison 至少包含:

- coverage。
- history depth。
- delisted/security survivorship support。
- corporate action handling。
- timestamp semantics。
- API stability。
- rate limits。
- cost。
- license restrictions。
- redistribution rights。
- export/storage permission。
- data correction/revision policy。
- support and SLA。

## 9. Phase 3 manifest impact

机构数据接入后,manifest 必须增强:

- contract/license id。
- usage scope。
- export restriction。
- redistribution_allowed。
- provider correction policy。
- vendor data version。
- migration mapping from old dataset ids。

不能因为换了高价 vendor 就降低 data audit gate。

## 10. Long-term north star

v1.3 的长期方向:

```text
strategy idea
-> data requirement
-> provider capability proof
-> reproducible dataset snapshot
-> quality and audit verdict
-> backtest evidence
-> risk review
-> paper observation
-> human decision
```

数据底座越强,越应该让晋级流程更清楚,而不是更松。

