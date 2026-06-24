from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from quant.live.alerts import AlertManager
from quant.live.events import EventJournal
from quant.live.store import OmsStore
from quant.live.types import AlertSeverity, EngineState


class RuntimeMonitor:
    def __init__(
        self,
        *,
        store: OmsStore,
        journal: EventJournal,
        alert_manager: AlertManager,
        market_data_staleness_sec: int,
        run_id: str,
        strategy_id: str,
        account_id: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.journal = journal
        self.alert_manager = alert_manager
        self.market_data_staleness_sec = market_data_staleness_sec
        self.run_id = run_id
        self.strategy_id = strategy_id
        self.account_id = account_id
        self.clock = clock or (lambda: datetime.now().astimezone())

    def check_market_data(
        self,
        *,
        now: datetime,
        last_bar_at: datetime | None,
    ) -> EngineState | None:
        if (
            last_bar_at is not None
            and (now - last_bar_at).total_seconds() <= self.market_data_staleness_sec
        ):
            return None

        state = self._set_safe_state(EngineState.FREEZE_OPEN, "market_data_stale", now)
        self._append_engine_state(state, "market_data_stale")
        self.alert_manager.emit(
            AlertSeverity.WARN,
            "market_data_stale",
            "market data is stale; opening orders are frozen",
            self._base_payload(now, last_bar_at=last_bar_at),
        )
        return state

    def on_gateway_disconnect(self, reason: str) -> EngineState:
        now = self.clock()
        state = self._set_safe_state(EngineState.FREEZE_OPEN, reason, now)
        self._append_engine_state(state, reason)
        self.alert_manager.emit(
            AlertSeverity.CRIT,
            "gateway_disconnect",
            "gateway disconnected; opening orders are frozen",
            self._base_payload(now, reason=reason),
        )
        return state

    def on_gateway_reconnect(self, *, reconciliation_ok: bool) -> EngineState:
        if not reconciliation_ok:
            return self.store.get_engine_state()

        current = self.store.get_engine_state()
        state = resolve_engine_state_transition(
            current,
            EngineState.NORMAL,
            allow_halt_resume=False,
        )
        if state == current:
            return current

        self.store.set_engine_state(
            state,
            "gateway_reconnected_reconciliation_ok",
            updated_at=self.clock(),
        )
        self.journal.append(
            "engine_state",
            {
                "state": state.value,
                "reason": "gateway_reconnected_reconciliation_ok",
            },
        )
        return state

    def _set_safe_state(
        self,
        state: EngineState,
        reason: str,
        updated_at: datetime,
    ) -> EngineState:
        current = self.store.get_engine_state()
        target = resolve_engine_state_transition(current, state)
        if target == current:
            return current
        self.store.set_engine_state(target, reason, updated_at=updated_at)
        return target

    def _append_engine_state(self, state: EngineState, reason: str) -> None:
        self.journal.append(
            "engine_state",
            {
                "state": state.value,
                "reason": reason,
            },
        )

    def _base_payload(
        self,
        now: datetime,
        *,
        reason: str | None = None,
        last_bar_at: datetime | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": self.run_id,
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "last_event_seq": self.journal.last_seq,
            "local_time": now.isoformat(),
            "market_time": now.isoformat(),
        }
        if reason is not None:
            payload["reason"] = reason
        if last_bar_at is not None:
            payload["last_bar_at"] = last_bar_at.isoformat()
        return payload


def resolve_engine_state_transition(
    current: EngineState,
    requested: EngineState,
    *,
    allow_halt_resume: bool = False,
) -> EngineState:
    if current == EngineState.HALT and requested != EngineState.HALT and not allow_halt_resume:
        return current
    return requested
