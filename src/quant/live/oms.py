from dataclasses import asdict, replace
from datetime import datetime
from typing import Any, Protocol

from quant.core.contract import Account, Order, OrderSide, OrderStatus, OrderType, Position, Trade
from quant.live.events import EventJournal
from quant.live.store import OmsStore
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, EngineState, OrderRequest
from quant.risk.pipeline import RiskEngine


class GatewayLike(Protocol):
    def send_order(self, req: OrderRequest) -> str: ...

    def cancel_order(self, broker_order_id: str) -> None: ...

    def query_account(self) -> Account: ...

    def query_positions(self) -> dict[str, Position]: ...

    def query_orders(self, active_only: bool = True) -> list[BrokerOrderSnapshot]: ...


class OrderManager:
    def __init__(
        self,
        *,
        account_id: str,
        gateway: GatewayLike,
        store: OmsStore,
        journal: EventJournal,
        risk: RiskEngine,
    ) -> None:
        self.account_id = account_id
        self.gateway = gateway
        self.store = store
        self.journal = journal
        self.risk = risk

    def submit_order(
        self,
        *,
        strategy_id: str,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None,
        type: OrderType,
        latest_price: float,
        now: datetime,
    ) -> str:
        order_id = self._next_order_id()
        req = OrderRequest(
            order_id=order_id,
            strategy_id=strategy_id,
            account_id=self.account_id,
            symbol=symbol,
            side=side,
            type=type,
            qty=qty,
            price=price,
            created_at=now,
        )
        order = Order(
            order_id=order_id,
            strategy_id=strategy_id,
            account_id=self.account_id,
            symbol=symbol,
            side=side,
            type=type,
            qty=qty,
            price=price,
            status=OrderStatus.SUBMITTING,
            filled_qty=0,
            remaining_qty=qty,
            avg_fill_price=0,
            created_at=now,
            updated_at=now,
        )

        try:
            account = self.gateway.query_account()
            positions = self.gateway.query_positions()
        except Exception as error:
            reason = f"gateway_query_error: {error}"
            rejected = replace(order, status=OrderStatus.REJECTED, reject_reason=reason)
            self.store.save_order(rejected)
            self._append_rejection("gateway_query_error", reason, rejected)
            self._append_order_event(rejected)
            self.freeze_open(reason)
            return order_id

        decision = self.risk.check_order(
            req,
            latest_price=latest_price,
            account=account,
            positions=positions,
            active_orders=self.store.list_orders(active_only=True),
            now=now,
            state=self.store.get_engine_state(),
        )
        if not decision.allowed:
            reason = _risk_reject_reason(decision.rule_id, decision.reason)
            rejected = replace(order, status=OrderStatus.REJECTED, reject_reason=reason)
            self.store.save_order(rejected)
            self._append_rejection(decision.rule_id or "risk_reject", reason, rejected)
            self._append_order_event(rejected)
            if decision.rule_id == "risk_engine_error":
                self.freeze_open(reason)
            return order_id

        self.store.save_order(order)
        try:
            broker_order_id = self.gateway.send_order(req)
        except Exception as error:
            reason = f"gateway_send_error: {error}"
            failed = replace(order, status=OrderStatus.REJECTED, reject_reason=reason)
            self.store.update_order(failed)
            self._append_rejection("gateway_send_error", reason, failed)
            self._append_order_event(failed)
            self.freeze_open(reason)
            return order_id

        submitted = replace(
            order,
            status=OrderStatus.SUBMITTED,
            broker_order_id=broker_order_id,
            updated_at=now,
        )
        self.store.update_order(submitted)
        self._append_order_event(submitted)
        return order_id

    def cancel_order(self, order_id: str) -> None:
        order = self.store.get_order(order_id)
        if order.broker_order_id is None:
            self.journal.append(
                "manual_ops",
                {
                    "action": "cancel_order",
                    "order_id": order.order_id,
                    "result": "no_broker_order_id",
                },
            )
            return
        self.gateway.cancel_order(order.broker_order_id)
        self.journal.append(
            "manual_ops",
            {
                "action": "cancel_order",
                "order_id": order.order_id,
                "broker_order_id": order.broker_order_id,
                "result": "requested",
            },
        )

    def on_broker_order(self, snapshot: BrokerOrderSnapshot) -> Order:
        order = self.store.get_order(snapshot.order_id)
        updated = replace(
            order,
            symbol=snapshot.symbol,
            side=snapshot.side,
            type=snapshot.type,
            qty=snapshot.qty,
            price=snapshot.price,
            status=snapshot.status,
            filled_qty=snapshot.filled_qty,
            remaining_qty=snapshot.remaining_qty,
            avg_fill_price=snapshot.avg_fill_price,
            updated_at=snapshot.updated_at,
            broker_order_id=snapshot.broker_order_id,
        )
        self.store.update_order(updated)
        self.journal.append(
            "reconciliation",
            {
                "kind": "broker_order",
                "order_id": updated.order_id,
                "broker_order_id": updated.broker_order_id,
                "status": updated.status.value,
            },
        )
        self._append_order_event(updated)
        return updated

    def on_broker_trade(self, snapshot: BrokerTradeSnapshot) -> Trade | None:
        trade = Trade(
            trade_id=snapshot.broker_trade_id,
            order_id=snapshot.order_id,
            strategy_id=snapshot.strategy_id,
            account_id=snapshot.account_id,
            symbol=snapshot.symbol,
            side=snapshot.side,
            qty=snapshot.qty,
            price=snapshot.price,
            commission=snapshot.commission,
            dt=snapshot.dt,
            broker_order_id=snapshot.broker_order_id,
            broker_trade_id=snapshot.broker_trade_id,
        )
        if not self.store.save_trade_once(trade):
            return None

        self._append_trade_event(trade)
        self.store.save_account_snapshot(
            self.gateway.query_account(),
            self.gateway.query_positions(),
            snapshot.dt,
        )
        return trade

    def freeze_open(self, reason: str) -> None:
        self._set_engine_state(EngineState.FREEZE_OPEN, reason)

    def halt(self, reason: str) -> None:
        self._set_engine_state(EngineState.HALT, reason)

    def resume(self, reason: str) -> None:
        if not reason:
            return
        self._set_engine_state(EngineState.NORMAL, reason)

    def _next_order_id(self) -> str:
        value = self.store.load_kv("next_order_seq", 1)
        seq = int(value)
        self.store.save_kv("next_order_seq", seq + 1)
        return f"O-{seq}"

    def _set_engine_state(self, state: EngineState, reason: str) -> None:
        self.store.set_engine_state(state, reason)
        self.journal.append(
            "engine_state",
            {
                "state": state.value,
                "reason": reason,
            },
        )

    def _append_rejection(self, rule_id: str, reason: str, order: Order) -> None:
        self.journal.append(
            "risk_reject",
            {
                "rule_id": rule_id,
                "reason": reason,
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
            },
        )

    def _append_order_event(self, order: Order) -> None:
        self.journal.append("order", _order_payload(order))

    def _append_trade_event(self, trade: Trade) -> None:
        self.journal.append("trade", _trade_payload(trade))


def _risk_reject_reason(rule_id: str | None, reason: str | None) -> str:
    if rule_id and reason:
        return f"{rule_id}: {reason}"
    return reason or rule_id or "risk_reject"


def _order_payload(order: Order) -> dict[str, Any]:
    payload = asdict(order)
    payload["side"] = order.side.value
    payload["type"] = order.type.value
    payload["status"] = order.status.value
    payload["created_at"] = order.created_at.isoformat()
    payload["updated_at"] = order.updated_at.isoformat()
    return payload


def _trade_payload(trade: Trade) -> dict[str, Any]:
    payload = asdict(trade)
    payload["side"] = trade.side.value
    payload["dt"] = trade.dt.isoformat()
    return payload
