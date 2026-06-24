from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quant.core.contract import Position
from quant.live.events import EventJournal
from quant.live.gateway.base import GatewayBase
from quant.live.store import OmsStore
from quant.live.types import EngineState


class ReconciliationStatus(StrEnum):
    OK = "OK"
    REPAIRED = "REPAIRED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ReconciliationResult:
    status: ReconciliationStatus
    cash_diff: float
    position_diffs: dict[str, float]
    message: str


class Reconciler:
    def __init__(
        self,
        *,
        store: OmsStore,
        gateway: GatewayBase,
        journal: EventJournal,
        cash_tolerance: float,
        position_qty_tolerance: float,
        auto_repair_cash_drift_below: float,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self.journal = journal
        self.cash_tolerance = cash_tolerance
        self.position_qty_tolerance = position_qty_tolerance
        self.auto_repair_cash_drift_below = auto_repair_cash_drift_below

    def run(self, startup: bool) -> ReconciliationResult:
        snapshot = self.store.load_account_snapshot()
        if snapshot is None:
            return self._fail(
                startup=startup,
                cash_diff=0.0,
                position_diffs={},
                message="missing local account snapshot",
            )

        gateway_account = self.gateway.query_account()
        gateway_positions = self.gateway.query_positions()

        cash_diff = snapshot.account.cash - gateway_account.cash
        position_diffs = self._position_diffs(snapshot.positions, gateway_positions)

        if self._position_failure(position_diffs):
            return self._fail(
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                message="position drift exceeds tolerance",
            )

        abs_cash_diff = abs(cash_diff)
        if abs_cash_diff <= self.cash_tolerance:
            return self._record(
                ReconciliationStatus.OK,
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                message="reconciled",
            )

        if abs_cash_diff <= self.auto_repair_cash_drift_below:
            self.store.save_account_snapshot(
                gateway_account,
                gateway_positions,
                datetime.now().astimezone(),
            )
            return self._record(
                ReconciliationStatus.REPAIRED,
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                message="repaired cash drift",
            )

        return self._fail(
            startup=startup,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            message="cash drift exceeds repair threshold",
        )

    def _position_failure(self, position_diffs: dict[str, float]) -> bool:
        return any(abs(diff) > self.position_qty_tolerance for diff in position_diffs.values())

    def _position_diffs(
        self,
        local_positions: dict[str, Position],
        gateway_positions: dict[str, Position],
    ) -> dict[str, float]:
        symbols = set(local_positions) | set(gateway_positions)
        diffs: dict[str, float] = {}
        for symbol in sorted(symbols):
            local_qty = local_positions.get(symbol).qty if symbol in local_positions else 0.0
            gateway_qty = gateway_positions.get(symbol).qty if symbol in gateway_positions else 0.0
            diff = local_qty - gateway_qty
            if diff != 0:
                diffs[symbol] = diff
        return diffs

    def _record(
        self,
        status: ReconciliationStatus,
        *,
        startup: bool,
        cash_diff: float,
        position_diffs: dict[str, float],
        message: str,
    ) -> ReconciliationResult:
        result = ReconciliationResult(
            status=status,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            message=message,
        )
        self.journal.append(
            "reconciliation",
            {
                "startup": startup,
                "status": status.value,
                "cash_diff": cash_diff,
                "position_diffs": position_diffs,
                "message": message,
            },
        )
        return result

    def _fail(
        self,
        *,
        startup: bool,
        cash_diff: float,
        position_diffs: dict[str, float],
        message: str,
    ) -> ReconciliationResult:
        self.store.set_engine_state(EngineState.HALT, message)
        return self._record(
            ReconciliationStatus.FAILED,
            startup=startup,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            message=message,
        )
