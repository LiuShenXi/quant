import sqlite3
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant.core.contract import Account, Order, OrderSide, OrderStatus, OrderType, Position, Trade
from quant.live.store import OmsStore
from quant.live.types import EngineState


def make_order(status: OrderStatus = OrderStatus.SUBMITTED) -> Order:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    return Order(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.2,
        status=status,
        filled_qty=0,
        remaining_qty=1000,
        avg_fill_price=0,
        created_at=now,
        updated_at=now,
    )


def test_store_persists_order_mapping_and_engine_state(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    assert store.is_empty() is True
    store.save_order(make_order())
    store.map_broker_order_id("O-1", "PAPER-O-1")
    store.set_engine_state(EngineState.FREEZE_OPEN, "disconnect")

    reopened = OmsStore(tmp_path / "meta.db")
    reopened.init_schema()
    assert reopened.get_order("O-1").broker_order_id == "PAPER-O-1"
    assert reopened.get_order_id_by_broker("PAPER-O-1") == "O-1"
    assert reopened.get_engine_state() == EngineState.FREEZE_OPEN
    assert reopened.is_empty() is False


def test_store_engine_state_accepts_deterministic_timestamp(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    updated_at = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))

    store.set_engine_state(EngineState.FREEZE_OPEN, "disconnect", updated_at=updated_at)

    with sqlite3.connect(tmp_path / "meta.db") as conn:
        row = conn.execute("SELECT updated_at FROM engine_state WHERE id = 1").fetchone()
    assert row[0] == updated_at.isoformat()


def test_store_update_order_raises_for_missing_order(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()

    with pytest.raises(KeyError) as exc_info:
        store.update_order(make_order())

    assert exc_info.value.args == ("O-1",)


def test_store_map_broker_order_id_raises_for_missing_order(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()

    with pytest.raises(KeyError) as exc_info:
        store.map_broker_order_id("O-404", "PAPER-O-404")

    assert exc_info.value.args == ("O-404",)


def test_store_closes_connections_after_methods(tmp_path, monkeypatch) -> None:
    real_connect = sqlite3.connect
    connections: list[TrackedConnection] = []

    def connect(*args, **kwargs):
        connection = TrackedConnection(real_connect(*args, **kwargs))
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)

    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    store.save_order(make_order())
    assert store.get_order("O-1").order_id == "O-1"

    assert connections
    assert all(connection.closed for connection in connections)


def test_store_update_order_persists_changes(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    store.save_order(make_order())

    updated = replace(
        make_order(),
        status=OrderStatus.PARTIAL,
        filled_qty=250,
        remaining_qty=750,
        avg_fill_price=3.21,
        broker_order_id="PAPER-O-1",
    )
    store.update_order(updated)

    loaded = store.get_order("O-1")
    assert loaded.status is OrderStatus.PARTIAL
    assert loaded.filled_qty == 250
    assert loaded.remaining_qty == 750
    assert loaded.avg_fill_price == 3.21
    assert loaded.broker_order_id == "PAPER-O-1"


def test_store_lists_active_orders_only(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    orders = [
        replace(make_order(OrderStatus.SUBMITTING), order_id="O-1"),
        replace(make_order(OrderStatus.SUBMITTED), order_id="O-2"),
        replace(make_order(OrderStatus.PARTIAL), order_id="O-3"),
        replace(make_order(OrderStatus.FILLED), order_id="O-4"),
        replace(make_order(OrderStatus.CANCELLED), order_id="O-5"),
        replace(make_order(OrderStatus.REJECTED), order_id="O-6"),
    ]
    for order in orders:
        store.save_order(order)

    assert [order.order_id for order in store.list_orders(active_only=True)] == [
        "O-1",
        "O-2",
        "O-3",
    ]


def test_store_deduplicates_trades_by_broker_trade_id(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    now = datetime(2024, 1, 3, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    trade = Trade(
        trade_id="T-1",
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=500,
        price=3.2,
        commission=5,
        dt=now,
        broker_order_id="PAPER-O-1",
        broker_trade_id="PAPER-T-1",
    )

    assert store.save_trade_once(trade) is True
    assert store.save_trade_once(trade) is False
    assert len(store.list_trades()) == 1


def test_store_raises_unrelated_trade_integrity_errors(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    now = datetime(2024, 1, 3, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    trade = Trade(
        trade_id="T-1",
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=500,
        price=3.2,
        commission=5,
        dt=now,
        broker_order_id="PAPER-O-1",
        broker_trade_id="PAPER-T-1",
    )

    assert store.save_trade_once(trade) is True
    with pytest.raises(sqlite3.IntegrityError):
        store.save_trade_once(replace(trade, broker_trade_id="PAPER-T-2"))


def test_store_persists_account_and_position_snapshot(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    now = datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    account = Account("paper", "CNY", cash=98_395, frozen=0, market_value=1_500, total_value=99_895)
    positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=500,
            sellable=0,
            avg_price=3.0,
            market_value=1_500,
        )
    }

    store.save_account_snapshot(account, positions, now)
    snapshot = store.load_account_snapshot()
    assert snapshot.account.cash == 98_395
    assert snapshot.positions["510300.SH"].qty == 500
    assert snapshot.updated_at == now


def test_store_round_trips_kv_values_and_defaults(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()

    assert store.load_kv("cursor", default={"page": 0}) == {"page": 0}

    store.save_kv("cursor", {"page": 2, "symbols": ["510300.SH", "159915.SZ"]})
    assert store.load_kv("cursor") == {
        "page": 2,
        "symbols": ["510300.SH", "159915.SZ"],
    }


def test_store_allocates_order_ids_atomically(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()

    assert store.next_order_id() == "O-1"
    assert store.next_order_id() == "O-2"

    reopened = OmsStore(tmp_path / "meta.db")
    reopened.init_schema()
    assert reopened.next_order_id() == "O-3"


class TrackedConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.closed = False

    @property
    def row_factory(self):
        return self.connection.row_factory

    @row_factory.setter
    def row_factory(self, value) -> None:
        self.connection.row_factory = value

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.connection.__exit__(exc_type, exc_value, traceback)

    def close(self) -> None:
        self.closed = True
        self.connection.close()

    def __getattr__(self, name: str):
        return getattr(self.connection, name)
