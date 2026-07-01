# 04 · 回测、执行与账户

## 1. BacktestClock

v1.2 回测主循环应从“按 A股日 session 分组”升级为“按 calendar 生成的主频事件流”。

```text
load strategy
load dataset manifest
build primary timeline from calendar + primary freq
for each timestamp in timeline:
    mark newly visible bars for every configured freq
    match orders that were created before this timestamp
    update portfolio and current bars
    call strategy callbacks for primary bars
    collect target/order intents
    run risk checks
    enqueue orders for future matching
    record equity and events
```

旧 A股日线行为可由 `calendar=cn_a_share`、`primary=1d`、`settlement=t1`、`fill=open_next_bar` 表达。

## 2. Context API 增量

保持旧接口可用:

```python
ctx.history(symbol, n, freq="1d", fields=None, adjust="qfq")
ctx.get_bar(symbol, freq="1d")
ctx.set_target(symbol, target_qty)
```

v1.2 第一轮必须新增:

```python
ctx.set_target_value(symbol, target_value)
ctx.set_target_weight(symbol, target_weight)
ctx.get_visible_bar_time(freq)
```

`set_target_weight` 是 Slice C 的必交付接口。策略表达“目标组合权重”，框架负责读取账户权益、当前 mark price、instrument metadata、qty step、lot size、fractional 规则和风险上限，再生成目标数量与订单。策略不得为了表达 60/40 这类组合目标而自行计算账户估值、交易单位或报价币种换算。

最小语义:

- `target_weight` 以账户总权益为分母，范围默认 `0.0 <= weight <= 1.0`；是否允许 short/杠杆由 risk config 显式声明。
- 多个 `set_target_weight` 在同一决策时刻组成一个 target batch。
- batch 总权重超过风险允许上限时，框架拒绝或按配置归一化，并写 risk event。
- `set_target_value` 的 value 必须声明或继承 account quote currency。
- target intent 事件记录 signal timestamp、source bar timestamp、target weight/value、估值价格和转换后的 target qty。

## 3. Target To Order

目标转换规则必须由 instrument/account metadata 驱动:

- `qty_step`: 数量最小递增。
- `lot_size`: 最小下单单位。
- `t_plus`: 0 或 1。
- `allow_fractional`: 是否允许小数数量。
- `cash_symbol` 或 `quote_currency`: 现金状态的记账标识。

spot/fractional 场景允许 `qty=0.001` 这类数量；A股 ETF 仍按整手/qty_step 向下取整。

## 4. Quote Currency Portfolio

`Portfolio` 不应固定 `currency="CNY"`。账户币种来自配置:

```yaml
account:
  currency: USD
  settlement: t0
  allow_fractional: true
```

估值规则:

- 所有 risky positions 按当前 mark price 转为 quote currency market value。
- cash 是 quote currency 余额。
- stablecoin 或 cash proxy 在 v1.2 只作为零收益 quote-currency cash 状态处理。
- 如果后续需要 USDT/USDC depeg、custody、yield 风险，应作为独立风险/数据模型，不混入 alpha 逻辑。

## 5. Fill Semantics

第一轮保留保守撮合:

- 信号在 bar close 产生。
- 订单最早在下一根可执行 bar 撮合。
- market order 用下一 bar open 加减 slippage。
- limit order 仍按 bar high/low 是否触达判断。
- 7x24 calendar 下不存在 A股涨跌停/停牌默认规则，除非 instrument metadata 显式提供。

每个 fill 都必须写入:

- order id
- trade id
- strategy id
- account id
- symbol
- side
- qty
- fill price
- fee
- estimated slippage cost
- timestamp
