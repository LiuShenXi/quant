from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(StrEnum):
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class EngineState(StrEnum):
    NORMAL = "NORMAL"
    FREEZE_OPEN = "FREEZE_OPEN"
    HALT = "HALT"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    type: str
    exchange: str
    list_date: date
    delist_date: date | None
    lot_size: int
    qty_step: int
    tick_size: float
    t_plus: int
    status: str


@dataclass(frozen=True)
class Bar:
    symbol: str
    freq: str
    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pre_close: float | None = None
    limit_up: float | None = None
    limit_down: float | None = None
    suspended: bool = False

    def __post_init__(self) -> None:
        if self.dt.tzinfo is None or self.dt.utcoffset() is None:
            raise ValueError("Bar.dt must be timezone-aware and represent the bar end time")


@dataclass(frozen=True)
class Order:
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    status: OrderStatus
    filled_qty: float
    remaining_qty: float
    avg_fill_price: float
    created_at: datetime
    updated_at: datetime
    broker_order_id: str | None = None
    reject_reason: str | None = None


@dataclass(frozen=True)
class Trade:
    trade_id: str
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    commission: float
    dt: datetime
    broker_order_id: str | None = None
    broker_trade_id: str | None = None


@dataclass(frozen=True)
class Position:
    symbol: str
    account_id: str
    qty: float
    sellable: float
    avg_price: float
    market_value: float


@dataclass(frozen=True)
class Account:
    account_id: str
    currency: str
    cash: float
    frozen: float
    market_value: float
    total_value: float


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    created_at: datetime


@dataclass(frozen=True)
class BrokerOrderSnapshot:
    broker_order_id: str
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    status: OrderStatus
    filled_qty: float
    remaining_qty: float
    avg_fill_price: float
    updated_at: datetime


@dataclass(frozen=True)
class BrokerTradeSnapshot:
    broker_trade_id: str
    broker_order_id: str
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    commission: float
    dt: datetime


@dataclass(frozen=True)
class Alert:
    severity: AlertSeverity
    key: str
    message: str
    created_at: datetime
    payload: dict[str, object]
