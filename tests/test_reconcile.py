import json
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, Position
from quant.live.events import EventJournal
from quant.live.reconcile import Reconciler, ReconciliationStatus
from quant.live.store import OmsStore
from quant.live.types import EngineState


class GatewayForReconcile:
    def __init__(self, cash: float, positions: dict[str, Position] | None = None) -> None:
        self.cash = cash
        self.positions = positions or {}

    def query_account(self) -> Account:
        return Account("paper", "CNY", self.cash, 0, 0, self.cash)

    def query_positions(self) -> dict[str, Position]:
        return self.positions

    def query_orders(self, active_only: bool = True):
        return []


def account_updated_at() -> datetime:
    return datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def make_snapshot(
    store: OmsStore,
    cash: float,
    positions: dict[str, Position] | None = None,
) -> None:
    account = Account("paper", "CNY", cash, 0, 0, cash)
    store.save_account_snapshot(account, positions or {}, account_updated_at())


def read_events(path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_reconcile_ok_when_cash_and_positions_match(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(store, 100_000)

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=True)

    assert result.status == ReconciliationStatus.OK
    assert result.cash_diff == 0
    assert result.position_diffs == {}
    assert result.message == "reconciled"
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["type"] == "reconciliation"
    assert events[-1]["payload"]["status"] == ReconciliationStatus.OK.value


def test_startup_reconcile_fails_when_local_snapshot_is_missing(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=True)

    assert result.status == ReconciliationStatus.FAILED
    assert result.position_diffs == {}
    assert store.get_engine_state() == EngineState.HALT
    assert store.load_account_snapshot() is None
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["type"] == "reconciliation"
    assert events[-1]["payload"]["status"] == ReconciliationStatus.FAILED.value
    assert events[-1]["payload"]["message"]


def test_reconcile_repairs_small_cash_drift(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(store, 100_000)

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(99_999.5),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.REPAIRED
    assert result.cash_diff == 0.5
    assert store.load_account_snapshot().account.cash == 99_999.5
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["payload"]["status"] == ReconciliationStatus.REPAIRED.value


def test_reconcile_halts_when_position_diff_exceeds_tolerance(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(
        store,
        100_000,
        {
            "510300.SH": Position(
                "510300.SH",
                "paper",
                qty=100,
                sellable=100,
                avg_price=3.0,
                market_value=300,
            )
        },
    )

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.FAILED
    assert result.cash_diff == 0
    assert result.position_diffs == {"510300.SH": 100}
    assert store.get_engine_state() == EngineState.HALT
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["payload"]["status"] == ReconciliationStatus.FAILED.value
