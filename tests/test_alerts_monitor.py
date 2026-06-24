import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant.live.alerts import AlertManager
from quant.live.events import EventJournal
from quant.live.monitor import RuntimeMonitor
from quant.live.store import OmsStore
from quant.live.types import AlertSeverity, EngineState


def test_alert_manager_deduplicates_by_key(tmp_path) -> None:
    manager = AlertManager(EventJournal(tmp_path / "events.jsonl"), dedupe_sec=300)
    payload = {
        "run_id": "paper-20240102",
        "strategy_id": "dual_ma_510300",
        "account_id": "paper",
        "last_event_seq": 7,
        "local_time": "2024-01-02T09:31:00+08:00",
        "market_time": "2024-01-02T09:31:00+08:00",
    }
    assert manager.emit(AlertSeverity.CRIT, "gateway_down", "gateway disconnected", payload) is True
    assert (
        manager.emit(AlertSeverity.CRIT, "gateway_down", "gateway disconnected", payload)
        is False
    )


def test_crit_alert_requires_location_fields(tmp_path) -> None:
    manager = AlertManager(EventJournal(tmp_path / "events.jsonl"), dedupe_sec=300)

    try:
        manager.emit(AlertSeverity.CRIT, "bad", "missing context", {"run_id": "paper-20240102"})
    except ValueError as exc:
        assert "CRIT alert missing fields" in str(exc)
    else:
        raise AssertionError("CRIT alert without required context was accepted")


def test_crit_alert_rejects_unusable_required_fields(tmp_path) -> None:
    manager = AlertManager(EventJournal(tmp_path / "events.jsonl"), dedupe_sec=300)

    for field, value in (
        ("run_id", None),
        ("strategy_id", ""),
        ("account_id", "   "),
        ("local_time", None),
        ("market_time", ""),
    ):
        payload = {
            "run_id": "paper-20240102",
            "strategy_id": "dual_ma_510300",
            "account_id": "paper",
            "last_event_seq": 7,
            "local_time": "2024-01-02T09:31:00+08:00",
            "market_time": "2024-01-02T09:31:00+08:00",
        }
        payload[field] = value

        try:
            manager.emit(AlertSeverity.CRIT, "bad", "missing context", payload)
        except ValueError as exc:
            assert field in str(exc)
        else:
            raise AssertionError(f"CRIT alert accepted unusable {field!r}")


def test_crit_alert_writes_required_context_into_event(tmp_path) -> None:
    journal_path = tmp_path / "events.jsonl"
    manager = AlertManager(EventJournal(journal_path), dedupe_sec=300)
    payload = {
        "run_id": "paper-20240102",
        "strategy_id": "dual_ma_510300",
        "account_id": "paper",
        "last_event_seq": 7,
        "local_time": "2024-01-02T09:31:00+08:00",
        "market_time": "2024-01-02T09:31:00+08:00",
    }

    assert manager.emit(AlertSeverity.CRIT, "gateway_down", "gateway disconnected", payload)

    event = json.loads(journal_path.read_text(encoding="utf-8").strip())
    assert event["type"] == "alert"
    assert event["payload"]["severity"] == AlertSeverity.CRIT.value
    assert event["payload"]["key"] == "gateway_down"
    assert event["payload"]["message"] == "gateway disconnected"
    assert event["payload"]["run_id"] == payload["run_id"]
    assert event["payload"]["strategy_id"] == payload["strategy_id"]
    assert event["payload"]["account_id"] == payload["account_id"]
    assert event["payload"]["last_event_seq"] == payload["last_event_seq"]
    assert event["payload"]["local_time"] == payload["local_time"]
    assert event["payload"]["market_time"] == payload["market_time"]


def test_market_data_staleness_freezes_open(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(EventJournal(tmp_path / "alerts.jsonl"), dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )
    now = datetime(2024, 1, 2, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    state = monitor.check_market_data(now=now, last_bar_at=now - timedelta(seconds=90))
    assert state == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN


def test_market_data_staleness_preserves_halt_and_handles_missing_last_bar(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    store.set_engine_state(EngineState.HALT, "manual halt")
    alerts = EventJournal(tmp_path / "alerts.jsonl")
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(alerts, dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )
    now = datetime(2024, 1, 2, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    state = monitor.check_market_data(now=now, last_bar_at=None)

    assert state == EngineState.HALT
    assert store.get_engine_state() == EngineState.HALT
    event = json.loads(alerts.path.read_text(encoding="utf-8").strip())
    assert event["payload"]["severity"] == AlertSeverity.CRIT.value
    assert "last_bar_at" not in event["payload"]


def test_gateway_disconnect_freezes_and_gateway_reconnect_does_not_auto_resume(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(EventJournal(tmp_path / "alerts.jsonl"), dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )

    state = monitor.on_gateway_disconnect("network drill")

    assert state == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN
    assert monitor.on_gateway_reconnect(reconciliation_ok=False) == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN
    assert monitor.on_gateway_reconnect(reconciliation_ok=True) == EngineState.NORMAL
    assert store.get_engine_state() == EngineState.NORMAL


def test_halt_survives_disconnect_and_reconnect(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    store.set_engine_state(EngineState.HALT, "manual halt")
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(EventJournal(tmp_path / "alerts.jsonl"), dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )

    assert monitor.check_market_data(
        now=datetime(2024, 1, 2, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        last_bar_at=datetime(2024, 1, 2, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    ) == EngineState.HALT
    assert monitor.on_gateway_disconnect("network drill") == EngineState.HALT
    assert store.get_engine_state() == EngineState.HALT
    assert monitor.on_gateway_reconnect(reconciliation_ok=False) == EngineState.HALT
    assert monitor.on_gateway_reconnect(reconciliation_ok=True) == EngineState.HALT
    assert store.get_engine_state() == EngineState.HALT
