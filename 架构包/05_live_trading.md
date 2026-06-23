# 05 · 实盘交易层(OMS + Gateway)

实盘引擎 = 事件循环 + OMS(订单管理)+ 风控 + Gateway(券商适配器)。策略看到的世界与回测完全相同;本层的全部复杂度在于:真实世界会**断线、丢回报、部分成交、状态不明**。

## 1. Gateway 抽象(对接任何券商/交易所的唯一接口)

```python
# live/gateway/base.py
class GatewayBase(ABC):
    name: str
    @abstractmethod
    def connect(self, conf: dict) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
    @abstractmethod
    def subscribe(self, symbols: list[str]) -> None: ...
    @abstractmethod
    def send_order(self, req: OrderRequest) -> str: ...        # 返回 broker_order_id
    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None: ...
    @abstractmethod
    def query_account(self) -> Account: ...
    @abstractmethod
    def query_positions(self) -> dict[str, Position]: ...
    @abstractmethod
    def query_orders(self, active_only: bool = True) -> list[Order]: ...
    # 引擎注入回调:on_tick / on_bar / on_order / on_trade / on_disconnect
```

换市场 = 换一个 Gateway 实现 + 换合约表,核心层与策略零改动。

## 2. 订单状态机与 ID 映射

```
SUBMITTING ──发送成功──▶ SUBMITTED ──部分成交──▶ PARTIAL ──▶ FILLED
     │                        │                     │
     └──发送失败──▶ REJECTED   └────撤单───▶ CANCELLED(可带部分成交)
```

- 本地 `order_id` 在发送**前**生成并落库(SQLite `orders` 表),收到 broker_order_id 后回填映射。
- 任何状态变更先写库、再派发回调(write-ahead),崩溃后状态可恢复。

## 3. OMS 铁律

| 场景 | 规则 |
|---|---|
| 下单超时无回报 | **先查询、绝不盲目重发**(`query_orders` 确认状态;盲目重发是双倍下单事故的标准来源) |
| 成交回报去重 | 以 (broker_order_id, trade_id) 幂等,重复回报丢弃 |
| 断线重连 | on_disconnect → 冻结新开仓 → 重连后全量 query_orders/positions 同步 → 对账通过才恢复 |
| 单线程写 | 所有订单操作经由单一队列/线程执行,杜绝并发下单竞态 |
| 流水审计 | 每个订单/成交/拒绝事件同时追加写 JSONL 事件流水(只追加,不修改) |

## 4. 执行算法(execution/)

`set_target` 的差额由执行模块完成,内置三档,按策略配置选择:

1. **立即限价**:对价 ± 1 tick 挂limit,超时未成交撤单重挂,最多 N 次(默认)。
2. **再平衡器**:对全组合 target 与当前持仓做 diff,先卖后买(腾资金),自动处理 T+1 可卖、整手、涨跌停不可交易剔除。
3. **TWAP 切片**(可选):大单按时间均匀切 N 片,中低频偶尔需要。

执行参数(超时秒数、重挂次数、切片数)在策略实例 YAML 的 `execution:` 段配置。

## 5. 对账(Reconciliation)——实盘安全的基石

三个触发点:**启动时(强制)**、盘中定时(如每 30 分钟)、收盘后。

```
本地持仓/资金(SQLite) vs gateway.query_positions()/query_account()
差异 = 0           → 正常
差异 ≤ 容忍阈值     → 以券商为准修正本地,记录告警
差异 > 阈值        → 进入 FREEZE(禁止新开仓)+ 紧急告警,人工处理
```

启动对账未通过前,引擎拒绝接受任何策略订单。

## 6. Paper 模式(实盘前的强制关卡)

`SimGateway` 实现同一个 GatewayBase 接口:订阅**真实实时行情**,撮合在本地模拟(复用回测的 Matcher 和成本模型)。配置里 `mode: paper` 即启用——除了钱是假的,代码路径与实盘 100% 相同,用来暴露:行情时序问题、回调处理 bug、调度与重连逻辑、告警链路。

## 7. 各市场适配器要点

| 市场 | Gateway 实现 | 要点 |
|---|---|---|
| A股股票/ETF | `QmtGateway`(xtquant) | 需券商开通 QMT/miniQMT 权限;客户端须运行在 Windows;行情(xtdata)与交易(xttrader)同源,实盘进程部署在 Windows 机;委托状态经由回调+主动查询双通道兜底 |
| A股(替代) | Ptrade | 代码托管在券商服务器运行,架构上相当于把"实盘进程"整体搬过去,契约与策略不变 |
| 期货 | `CtpGateway`(直接复用 vn.py 的 CTP 网关,外面包一层适配) | CTP 有交易时段连接管理、结算确认等固定流程,vn.py 已处理,不要重写 |
| 加密货币 | `CcxtGateway` | REST 轮询 + WebSocket 行情;注意限频与时钟同步;7×24 运行对监控要求更高 |

合规提示:境内程序化交易需按规定通过券商/期货公司完成报备,并关注其对委托频率、撤单比例等的限制——开通权限时与券商确认,把相关上限写进 06 号文档的风控配置。
