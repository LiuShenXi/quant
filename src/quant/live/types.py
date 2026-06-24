from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quant.core.contract import OrderSide, OrderStatus, OrderType


class EngineState(StrEnum):
    NORMAL = "NORMAL"
    FREEZE_OPEN = "FREEZE_OPEN"
    HALT = "HALT"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


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
