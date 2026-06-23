# 03 · 策略接口契约(核心文档)

这份契约回答一个问题:**策略和平台之间的边界长什么样**。你打磨的策略只要符合本契约,就能不改一行代码地在回测、Paper、实盘三种模式间切换——这就是"打磨完直接接入"的实现机制。

## 1. 基础数据结构

```python
# core/types.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    BUY = "BUY"; SELL = "SELL"

class OrderType(str, Enum):
    LIMIT = "LIMIT"; MARKET = "MARKET"

class OrderStatus(str, Enum):
    SUBMITTING = "SUBMITTING"; SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"; FILLED = "FILLED"
    CANCELLED = "CANCELLED"; REJECTED = "REJECTED"

@dataclass(frozen=True)
class Bar:
    symbol: str
    dt: datetime              # bar 的结束时间
    open: float; high: float; low: float; close: float
    volume: float; amount: float

@dataclass(frozen=True)
class Order:
    order_id: str             # 本地ID,系统生成,全局唯一
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None       # MARKET 单为 None
    status: OrderStatus
    filled_qty: float
    avg_fill_price: float
    dt: datetime

@dataclass(frozen=True)
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    commission: float
    dt: datetime

@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float                # 总持仓
    sellable: float           # 今日可卖(T+1 标的次日 = qty)
    avg_price: float

@dataclass(frozen=True)
class Account:
    cash: float               # 可用资金
    frozen: float             # 挂单冻结
    total_value: float        # 现金 + 持仓市值
```

## 2. 策略生命周期

```python
# core/strategy.py
from abc import ABC, abstractmethod

class StrategyBase(ABC):
    def on_init(self, ctx: "Context") -> None: ...
        # 引擎装载策略后调用一次:读参数、预热指标。此时不可下单。
    def on_start(self, ctx: "Context") -> None: ...
        # 引擎启动(实盘=每个交易日盘前)。可恢复状态、检查持仓。
    @abstractmethod
    def on_bar(self, ctx: "Context", bar: Bar) -> None: ...
        # 主回调。订阅的每个标的、每根 bar 收线后触发一次。
    def on_trade(self, ctx: "Context", trade: Trade) -> None: ...
        # 每笔成交回报(可能部分成交、多次触发)。
    def on_order(self, ctx: "Context", order: Order) -> None: ...
        # 订单状态变化(含 REJECTED——风控拒单也走这里)。
    def on_timer(self, ctx: "Context", timer_id: str) -> None: ...
        # ctx.schedule() 注册的定时回调(如收盘前 N 分钟再平衡)。
    def on_stop(self, ctx: "Context") -> None: ...
        # 引擎停止(实盘=收盘后/手动停止)。保存状态。
```

时序保证:回调**串行执行**,同一策略实例永远不会被并发调用;`on_bar` 中下的单,其 `on_order/on_trade` 回报在之后的事件循环中送达(回测中同样异步语义,杜绝"下单即成交"的幻觉)。

## 3. Context API(策略可见的全部世界)

```python
# core/context.py
from typing import Protocol, Any, Sequence
import pandas as pd

class Context(Protocol):
    # —— 时间与参数 ——
    @property
    def now(self) -> datetime: ...            # 唯一合法时间来源
    @property
    def params(self) -> dict[str, Any]: ...   # 来自策略实例 YAML
    @property
    def mode(self) -> str: ...                # "backtest"/"paper"/"live",仅供日志,禁止用于分支逻辑

    # —— 数据(委托 DataService,自动截止到 now,物理上杜绝未来数据) ——
    def history(self, symbol: str, n: int, freq: str = "1d",
                fields: Sequence[str] | None = None,
                adjust: str = "qfq") -> pd.DataFrame: ...
    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None: ...
    def get_instrument(self, symbol: str) -> "Instrument": ...

    # —— 账户与持仓 ——
    def get_position(self, symbol: str) -> Position: ...
    def get_positions(self) -> dict[str, Position]: ...
    def get_account(self) -> Account: ...
    def get_open_orders(self) -> list[Order]: ...

    # —— 交易 ——
    def order(self, symbol: str, side: OrderSide, qty: float,
              price: float | None = None,
              type: OrderType = OrderType.LIMIT) -> str: ...   # 返回 order_id
    def cancel(self, order_id: str) -> None: ...
    def set_target(self, symbol: str, target_qty: float) -> None: ...
        # 目标仓位语义:声明"我想持有多少",差额由执行模块负责
        # (自动处理拆单、T+1可卖、整手取整)。中低频策略首选,出错率远低于手搓订单。

    # —— 定时、日志、状态 ——
    def schedule(self, timer_id: str, at: str) -> None: ...    # at="14:50" 每日触发
    def log(self, msg: str, level: str = "INFO") -> None: ...
    def save_state(self, key: str, value: Any) -> None: ...    # 持久化KV,重启后可恢复
    def load_state(self, key: str, default: Any = None) -> Any: ...
```

## 4. 交易语义约定

- `order()` 立即返回本地 `order_id`,**不保证成交**;结果通过 `on_order/on_trade` 异步回报。
- 部分成交是常态:一个订单可能触发多次 `on_trade`。
- 风控拒单表现为 `on_order` 收到 `REJECTED` 状态,reason 写入日志——策略应当能优雅处理被拒。
- `set_target` 与 `order` 不要混用同一标的,避免执行模块和策略互相打架。

## 5. 确定性守则(策略代码的禁令清单)

违反任何一条,"回测=实盘"的保证即失效。平台提供 lint 脚本在接入时静态扫描:

1. 禁止 `datetime.now()` / `time.time()` → 用 `ctx.now`。
2. 禁止未注入种子的随机数 → 需要随机时用 `ctx.params` 里的 seed。
3. 禁止直接网络请求、读写文件、读环境变量 → 数据走 `ctx.history`,状态走 `ctx.save_state`。
4. 禁止模块级可变全局状态、禁止跨策略实例共享对象。
5. 禁止 `ctx.mode` 参与逻辑分支(只许打日志)。
6. 可调参数一律进 YAML 的 `params`,禁止散落在代码常量里——否则参数追溯失效。

## 6. 策略实例配置(YAML schema)

一个策略类可以有多个实例(不同标的/参数),每个实例一份配置:

```yaml
# config/strategies/dual_ma_510300.yaml
id: dual_ma_510300            # 全局唯一实例ID,出现在所有日志和报表中
class: strategies.dual_ma:DualMA
version: "1.0.0"
universe: ["510300.SH"]       # 引擎据此订阅行情
freq: "1d"
params:
  symbol: "510300.SH"
  fast: 5
  slow: 20
  target_qty: 10000
risk:                          # 实例级风控上限(不能放宽全局风控,只能更严)
  max_order_value: 200_000
  max_position_value: 500_000
mode: backtest                 # backtest | paper | live —— 切换模式只改这一行
```

启动时由 pydantic 校验,字段缺失/类型错误直接拒绝启动。

## 7. 完整最小示例

```python
# strategies/dual_ma.py
from core.strategy import StrategyBase
from core.types import Bar

class DualMA(StrategyBase):
    def on_init(self, ctx):
        self.symbol = ctx.params["symbol"]
        self.fast = ctx.params["fast"]
        self.slow = ctx.params["slow"]

    def on_bar(self, ctx, bar: Bar):
        if bar.symbol != self.symbol:
            return
        close = ctx.history(self.symbol, self.slow + 1)["close"]
        if len(close) <= self.slow:
            return                          # 数据不足,跳过
        ma_fast = close.tail(self.fast).mean()
        ma_slow = close.tail(self.slow).mean()
        pos = ctx.get_position(self.symbol).qty
        if ma_fast > ma_slow and pos == 0:
            ctx.set_target(self.symbol, ctx.params["target_qty"])
        elif ma_fast < ma_slow and pos > 0:
            ctx.set_target(self.symbol, 0)
```

这个类不 import 任何回测库、券商 SDK、数据库——这正是契约的全部意义。

## 8. 版本与兼容性承诺(保证你以后的策略仍能直接接入)

- 契约接口(types / StrategyBase / Context)单独放在 `core/contract` 包,独立标注版本号。
- **只做增量演进**:新增方法/可选字段不升大版本;任何会破坏既有策略的改动必须升大版本,且旧接口保留一个大版本周期的适配层。
- 每次回测报告与实盘会话日志中记录:契约版本 + 策略 class + version + params 的哈希——任何一次历史结果都能精确追溯到当时的代码与参数。

## 9. 接入验收清单(满足即可"直接接入")

- [ ] 类继承 `StrategyBase`,实现 `on_bar`,不 import core/contract 之外的平台内部模块
- [ ] 通过确定性 lint 扫描(第 5 节六条)
- [ ] 有合法的实例 YAML,pydantic 校验通过
- [ ] 同一数据、同一参数,事件回测连跑两次,成交流水逐笔一致(确定性验证)
- [ ] 在回测引擎完整跑通目标区间,无未捕获异常
- [ ] (上实盘前)Paper 模式运行 ≥ 2 周,对账零差异 —— 见 09 号文档实盘准入清单
