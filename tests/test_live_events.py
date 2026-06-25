import inspect
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import OrderSide, OrderStatus, OrderType
from quant.live.events import EventJournal
from quant.live.gateway.base import GatewayBase
from quant.live.types import BrokerOrderSnapshot, EngineState, OrderRequest


def test_order_request_and_snapshot_are_stable_contracts() -> None:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    req = OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.2,
        created_at=now,
    )
    snapshot = BrokerOrderSnapshot(
        broker_order_id="PAPER-O-1",
        order_id=req.order_id,
        symbol=req.symbol,
        side=req.side,
        type=req.type,
        qty=req.qty,
        price=req.price,
        status=OrderStatus.SUBMITTED,
        filled_qty=0,
        remaining_qty=req.qty,
        avg_fill_price=0,
        updated_at=now,
    )
    assert snapshot.broker_order_id == "PAPER-O-1"
    assert EngineState.FREEZE_OPEN.value == "FREEZE_OPEN"


def test_event_journal_appends_jsonl_with_sequence(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    written_at = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    journal = EventJournal(path, clock=lambda: written_at)
    seq1 = journal.append("engine_state", {"state": "NORMAL"})
    seq2 = journal.append("order", {"order_id": "O-1", "status": "SUBMITTED"})

    assert (seq1, seq2) == (1, 2)
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [line["seq"] for line in lines] == [1, 2]
    assert lines[0]["type"] == "engine_state"
    assert lines[0]["written_at"] == written_at.isoformat()
    assert journal.last_seq == 2


def test_gateway_callbacks_accept_broker_snapshots() -> None:
    signature = inspect.signature(GatewayBase.set_callbacks)

    assert "BrokerOrderSnapshot" in str(signature.parameters["on_order"].annotation)
    assert "BrokerTradeSnapshot" in str(signature.parameters["on_trade"].annotation)
