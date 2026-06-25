import json
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, Position
from quant.live.events import EventJournal
from quant.live.reconcile import Reconciler, ReconciliationStatus
from quant.live.store import OmsStore
from quant.live.types import EngineState


class GatewayForReconcile:
    def __init__(
        self,
        cash: float,
        positions: dict[str, Position] | None = None,
        *,
        frozen: float = 0,
        market_value: float = 0,
        total_value: float | None = None,
    ) -> None:
        self.cash = cash
        self.positions = positions or {}
        self.frozen = frozen
        self.market_value = market_value
        self.total_value = cash if total_value is None else total_value

    def query_account(self) -> Account:
        return Account(
            "paper",
            "CNY",
            self.cash,
            self.frozen,
            self.market_value,
            self.total_value,
        )

    def query_positions(self) -> dict[str, Position]:
        return self.positions

    def query_orders(self, active_only: bool = True):
        return []


class FailingAccountGateway(GatewayForReconcile):
    def query_account(self) -> Account:
        raise RuntimeError("account offline")


def account_updated_at() -> datetime:
    return datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def make_snapshot(
    store: OmsStore,
    cash: float,
    positions: dict[str, Position] | None = None,
    *,
    frozen: float = 0,
    market_value: float = 0,
    total_value: float | None = None,
) -> None:
    account = Account(
        "paper",
        "CNY",
        cash,
        frozen,
        market_value,
        cash if total_value is None else total_value,
    )
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


def test_reconcile_uses_injected_clock_for_repair_snapshot_timestamp(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(store, 100_000)
    repaired_at = datetime(2024, 1, 3, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(99_999.5),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
        clock=lambda: repaired_at,
    )

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.REPAIRED
    assert store.load_account_snapshot().updated_at == repaired_at


def test_reconcile_gateway_query_exception_halts_and_audits_failure(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(store, 100_000)

    reconciler = Reconciler(
        store=store,
        gateway=FailingAccountGateway(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=True)

    assert result.status == ReconciliationStatus.FAILED
    assert result.message == "gateway_query_error: account offline"
    assert store.get_engine_state() == EngineState.HALT
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["type"] == "reconciliation"
    assert events[-1]["payload"]["startup"] is True
    assert events[-1]["payload"]["status"] == ReconciliationStatus.FAILED.value
    assert events[-1]["payload"]["message"] == "gateway_query_error: account offline"


def test_reconcile_repair_persistence_exception_halts_and_audits_failure(
    tmp_path,
    monkeypatch,
) -> None:
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

    def fail_snapshot_save(*args, **kwargs) -> None:
        raise RuntimeError("snapshot db offline")

    monkeypatch.setattr(store, "save_account_snapshot", fail_snapshot_save)

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.FAILED
    assert result.message == "snapshot_persist_error: snapshot db offline"
    assert store.get_engine_state() == EngineState.HALT
    events = read_events(tmp_path / "events.jsonl")
    assert events[-1]["type"] == "reconciliation"
    assert events[-1]["payload"]["status"] == ReconciliationStatus.FAILED.value
    assert events[-1]["payload"]["message"] == "snapshot_persist_error: snapshot db offline"


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


def test_reconcile_halts_when_account_value_fields_drift(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    make_snapshot(store, 100_000, frozen=10, market_value=1_000, total_value=101_010)

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(
            100_000,
            frozen=0,
            market_value=1_000,
            total_value=101_000,
        ),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.FAILED
    assert result.account_diffs == {"frozen": 10, "total_value": 10}
    assert store.get_engine_state() == EngineState.HALT


def test_reconcile_halts_when_position_value_fields_drift(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    local_positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=100,
            sellable=80,
            avg_price=3.0,
            market_value=300,
        )
    }
    gateway_positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=100,
            sellable=70,
            avg_price=3.0,
            market_value=310,
        )
    }
    make_snapshot(store, 100_000, local_positions)

    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(100_000, positions=gateway_positions),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )

    result = reconciler.run(startup=False)

    assert result.status == ReconciliationStatus.FAILED
    assert result.position_value_diffs == {
        "510300.SH.sellable": 10,
        "510300.SH.market_value": -10,
    }
    assert store.get_engine_state() == EngineState.HALT
