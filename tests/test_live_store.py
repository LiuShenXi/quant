from datetime import datetime
from zoneinfo import ZoneInfo

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
