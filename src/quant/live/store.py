import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from quant.core.contract import Account, Order, OrderSide, OrderStatus, OrderType, Position, Trade
from quant.live.types import EngineState


@dataclass(frozen=True)
class AccountSnapshot:
    account: Account
    positions: dict[str, Position]
    updated_at: datetime


class OmsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def init_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                  order_id TEXT PRIMARY KEY,
                  strategy_id TEXT NOT NULL,
                  account_id TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  type TEXT NOT NULL,
                  qty REAL NOT NULL,
                  price REAL,
                  status TEXT NOT NULL,
                  filled_qty REAL NOT NULL,
                  remaining_qty REAL NOT NULL,
                  avg_fill_price REAL NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  broker_order_id TEXT,
                  reject_reason TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_broker_order_id
                ON orders(broker_order_id)
                WHERE broker_order_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS trades (
                  trade_id TEXT PRIMARY KEY,
                  order_id TEXT NOT NULL,
                  strategy_id TEXT NOT NULL,
                  account_id TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  qty REAL NOT NULL,
                  price REAL NOT NULL,
                  commission REAL NOT NULL,
                  dt TEXT NOT NULL,
                  broker_order_id TEXT,
                  broker_trade_id TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS account_snapshots (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  account_id TEXT NOT NULL,
                  currency TEXT NOT NULL,
                  cash REAL NOT NULL,
                  frozen REAL NOT NULL,
                  market_value REAL NOT NULL,
                  total_value REAL NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS position_snapshots (
                  symbol TEXT PRIMARY KEY,
                  account_id TEXT NOT NULL,
                  qty REAL NOT NULL,
                  sellable REAL NOT NULL,
                  avg_price REAL NOT NULL,
                  market_value REAL NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS engine_state (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  state TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kv (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );
                """
            )

    def save_order(self, order: Order) -> None:
        values = _order_to_row(order)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    order_id, strategy_id, account_id, symbol, side, type, qty, price, status,
                    filled_qty, remaining_qty, avg_fill_price, created_at, updated_at,
                    broker_order_id, reject_reason
                )
                VALUES (
                    :order_id, :strategy_id, :account_id, :symbol, :side, :type, :qty, :price,
                    :status, :filled_qty, :remaining_qty, :avg_fill_price, :created_at,
                    :updated_at, :broker_order_id, :reject_reason
                )
                """,
                values,
            )

    def update_order(self, order: Order) -> None:
        values = _order_to_row(order)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET strategy_id = :strategy_id,
                    account_id = :account_id,
                    symbol = :symbol,
                    side = :side,
                    type = :type,
                    qty = :qty,
                    price = :price,
                    status = :status,
                    filled_qty = :filled_qty,
                    remaining_qty = :remaining_qty,
                    avg_fill_price = :avg_fill_price,
                    created_at = :created_at,
                    updated_at = :updated_at,
                    broker_order_id = :broker_order_id,
                    reject_reason = :reject_reason
                WHERE order_id = :order_id
                """,
                values,
            )
            if cursor.rowcount != 1:
                raise KeyError(order.order_id)

    def get_order(self, order_id: str) -> Order:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if row is None:
            raise KeyError(order_id)
        return _row_to_order(row)

    def list_orders(self, active_only: bool = False) -> list[Order]:
        sql = "SELECT * FROM orders"
        params: tuple[str, ...] = ()
        if active_only:
            sql += " WHERE status IN (?, ?, ?)"
            params = (
                OrderStatus.SUBMITTING.value,
                OrderStatus.SUBMITTED.value,
                OrderStatus.PARTIAL.value,
            )
        sql += " ORDER BY created_at, order_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_order(row) for row in rows]

    def save_trade_once(self, trade: Trade) -> bool:
        values = _trade_to_row(trade)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trades (
                    trade_id, order_id, strategy_id, account_id, symbol, side, qty, price,
                    commission, dt, broker_order_id, broker_trade_id
                )
                VALUES (
                    :trade_id, :order_id, :strategy_id, :account_id, :symbol, :side, :qty,
                    :price, :commission, :dt, :broker_order_id, :broker_trade_id
                )
                ON CONFLICT(broker_trade_id) DO NOTHING
                """,
                values,
            )
        return cursor.rowcount == 1

    def list_trades(self) -> list[Trade]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM trades ORDER BY dt, trade_id").fetchall()
        return [_row_to_trade(row) for row in rows]

    def next_order_id(self, prefix: str = "O") -> str:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT value FROM kv WHERE key = ?",
                ("next_order_seq",),
            ).fetchone()
            seq = int(json.loads(row["value"])) if row is not None else 1
            conn.execute(
                """
                INSERT INTO kv (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("next_order_seq", json.dumps(seq + 1)),
            )
        return f"{prefix}-{seq}"

    def save_account_snapshot(
        self,
        account: Account,
        positions: dict[str, Position],
        updated_at: datetime,
    ) -> None:
        account_values = asdict(account) | {"id": 1, "updated_at": updated_at.isoformat()}
        position_values = [
            asdict(position) | {"updated_at": updated_at.isoformat()}
            for position in positions.values()
        ]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO account_snapshots (
                    id, account_id, currency, cash, frozen, market_value, total_value, updated_at
                )
                VALUES (
                    :id, :account_id, :currency, :cash, :frozen, :market_value, :total_value,
                    :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    account_id = excluded.account_id,
                    currency = excluded.currency,
                    cash = excluded.cash,
                    frozen = excluded.frozen,
                    market_value = excluded.market_value,
                    total_value = excluded.total_value,
                    updated_at = excluded.updated_at
                """,
                account_values,
            )
            conn.execute("DELETE FROM position_snapshots")
            conn.executemany(
                """
                INSERT INTO position_snapshots (
                    symbol, account_id, qty, sellable, avg_price, market_value, updated_at
                )
                VALUES (
                    :symbol, :account_id, :qty, :sellable, :avg_price, :market_value, :updated_at
                )
                """,
                position_values,
            )

    def load_account_snapshot(self) -> AccountSnapshot | None:
        with self._connect() as conn:
            account_row = conn.execute("SELECT * FROM account_snapshots WHERE id = 1").fetchone()
            position_rows = conn.execute(
                "SELECT * FROM position_snapshots ORDER BY symbol"
            ).fetchall()
        if account_row is None:
            return None
        account = Account(
            account_id=account_row["account_id"],
            currency=account_row["currency"],
            cash=account_row["cash"],
            frozen=account_row["frozen"],
            market_value=account_row["market_value"],
            total_value=account_row["total_value"],
        )
        positions = {
            row["symbol"]: Position(
                symbol=row["symbol"],
                account_id=row["account_id"],
                qty=row["qty"],
                sellable=row["sellable"],
                avg_price=row["avg_price"],
                market_value=row["market_value"],
            )
            for row in position_rows
        }
        return AccountSnapshot(
            account=account,
            positions=positions,
            updated_at=datetime.fromisoformat(account_row["updated_at"]),
        )

    def is_empty(self) -> bool:
        with self._connect() as conn:
            for table in (
                "orders",
                "trades",
                "account_snapshots",
                "position_snapshots",
                "engine_state",
                "kv",
            ):
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if count:
                    return False
        return True

    def map_broker_order_id(self, order_id: str, broker_order_id: str) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE orders SET broker_order_id = ? WHERE order_id = ?",
                (broker_order_id, order_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(order_id)

    def get_order_id_by_broker(self, broker_order_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT order_id FROM orders WHERE broker_order_id = ?",
                (broker_order_id,),
            ).fetchone()
        if row is None:
            return None
        return row["order_id"]

    def set_engine_state(
        self,
        state: EngineState,
        reason: str,
        *,
        updated_at: datetime | None = None,
    ) -> None:
        timestamp = updated_at or datetime.now().astimezone()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO engine_state (id, state, reason, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (state.value, reason, timestamp.isoformat()),
            )

    def get_engine_state(self) -> EngineState:
        with self._connect() as conn:
            row = conn.execute("SELECT state FROM engine_state WHERE id = 1").fetchone()
        if row is None:
            return EngineState.NORMAL
        return EngineState(row["state"])

    def save_kv(self, key: str, value: object) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kv (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, json.dumps(value, ensure_ascii=False, default=str)),
            )

    def load_kv(self, key: str, default: object | None = None) -> object | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


def _order_to_row(order: Order) -> dict[str, Any]:
    data = asdict(order)
    data["side"] = order.side.value
    data["type"] = order.type.value
    data["status"] = order.status.value
    data["created_at"] = order.created_at.isoformat()
    data["updated_at"] = order.updated_at.isoformat()
    return data


def _row_to_order(row: sqlite3.Row) -> Order:
    return Order(
        order_id=row["order_id"],
        strategy_id=row["strategy_id"],
        account_id=row["account_id"],
        symbol=row["symbol"],
        side=OrderSide(row["side"]),
        type=OrderType(row["type"]),
        qty=row["qty"],
        price=row["price"],
        status=OrderStatus(row["status"]),
        filled_qty=row["filled_qty"],
        remaining_qty=row["remaining_qty"],
        avg_fill_price=row["avg_fill_price"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        broker_order_id=row["broker_order_id"],
        reject_reason=row["reject_reason"],
    )


def _trade_to_row(trade: Trade) -> dict[str, Any]:
    data = asdict(trade)
    data["side"] = trade.side.value
    data["dt"] = trade.dt.isoformat()
    return data


def _row_to_trade(row: sqlite3.Row) -> Trade:
    return Trade(
        trade_id=row["trade_id"],
        order_id=row["order_id"],
        strategy_id=row["strategy_id"],
        account_id=row["account_id"],
        symbol=row["symbol"],
        side=OrderSide(row["side"]),
        qty=row["qty"],
        price=row["price"],
        commission=row["commission"],
        dt=datetime.fromisoformat(row["dt"]),
        broker_order_id=row["broker_order_id"],
        broker_trade_id=row["broker_trade_id"],
    )
