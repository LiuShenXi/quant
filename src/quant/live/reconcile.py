from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quant.core.contract import Account, Position
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
    account_diffs: dict[str, float] | None = None
    position_value_diffs: dict[str, float] | None = None


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
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self.journal = journal
        self.cash_tolerance = cash_tolerance
        self.position_qty_tolerance = position_qty_tolerance
        self.auto_repair_cash_drift_below = auto_repair_cash_drift_below
        self.clock = clock or (lambda: datetime.now().astimezone())

    def run(self, startup: bool) -> ReconciliationResult:
        snapshot = self.store.load_account_snapshot()
        if snapshot is None:
            return self._fail(
                startup=startup,
                cash_diff=0.0,
                position_diffs={},
                account_diffs={},
                position_value_diffs={},
                message="missing local account snapshot",
            )

        try:
            gateway_account = self.gateway.query_account()
            gateway_positions = self.gateway.query_positions()
        except Exception as error:
            return self._fail(
                startup=startup,
                cash_diff=0.0,
                position_diffs={},
                account_diffs={},
                position_value_diffs={},
                message=f"gateway_query_error: {error}",
            )

        cash_diff = snapshot.account.cash - gateway_account.cash
        account_diffs = self._account_diffs(snapshot.account, gateway_account, cash_diff)
        position_diffs = self._position_diffs(snapshot.positions, gateway_positions)
        position_value_diffs = self._position_value_diffs(
            snapshot.positions,
            gateway_positions,
        )

        if account_diffs:
            return self._fail(
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                account_diffs=account_diffs,
                position_value_diffs=position_value_diffs,
                message="account drift exceeds tolerance",
            )

        if self._position_failure(position_diffs):
            return self._fail(
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                account_diffs=account_diffs,
                position_value_diffs=position_value_diffs,
                message="position drift exceeds tolerance",
            )

        if position_value_diffs:
            return self._fail(
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                account_diffs=account_diffs,
                position_value_diffs=position_value_diffs,
                message="position value drift exceeds tolerance",
            )

        abs_cash_diff = abs(cash_diff)
        if abs_cash_diff <= self.cash_tolerance:
            return self._record(
                ReconciliationStatus.OK,
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                account_diffs=account_diffs,
                position_value_diffs=position_value_diffs,
                message="reconciled",
            )

        if abs_cash_diff <= self.auto_repair_cash_drift_below:
            try:
                self.store.save_account_snapshot(
                    gateway_account,
                    gateway_positions,
                    self.clock(),
                )
            except Exception as error:
                return self._fail(
                    startup=startup,
                    cash_diff=cash_diff,
                    position_diffs=position_diffs,
                    account_diffs=account_diffs,
                    position_value_diffs=position_value_diffs,
                    message=f"snapshot_persist_error: {error}",
                )
            return self._record(
                ReconciliationStatus.REPAIRED,
                startup=startup,
                cash_diff=cash_diff,
                position_diffs=position_diffs,
                account_diffs=account_diffs,
                position_value_diffs=position_value_diffs,
                message="repaired cash drift",
            )

        return self._fail(
            startup=startup,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            account_diffs=account_diffs,
            position_value_diffs=position_value_diffs,
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

    def _account_diffs(
        self,
        local: Account,
        gateway: Account,
        cash_diff: float,
    ) -> dict[str, float]:
        diffs: dict[str, float] = {}
        for field in ("frozen", "market_value"):
            diff = getattr(local, field) - getattr(gateway, field)
            if abs(diff) > self.cash_tolerance:
                diffs[field] = diff
        total_value_diff = local.total_value - gateway.total_value
        non_cash_total_diff = total_value_diff - cash_diff
        if abs(non_cash_total_diff) > self.cash_tolerance:
            diffs["total_value"] = total_value_diff
        return diffs

    def _position_value_diffs(
        self,
        local_positions: dict[str, Position],
        gateway_positions: dict[str, Position],
    ) -> dict[str, float]:
        symbols = set(local_positions) | set(gateway_positions)
        diffs: dict[str, float] = {}
        for symbol in sorted(symbols):
            local = local_positions.get(symbol)
            gateway = gateway_positions.get(symbol)
            local_sellable = local.sellable if local is not None else 0.0
            gateway_sellable = gateway.sellable if gateway is not None else 0.0
            sellable_diff = local_sellable - gateway_sellable
            if abs(sellable_diff) > self.position_qty_tolerance:
                diffs[f"{symbol}.sellable"] = sellable_diff

            local_market_value = local.market_value if local is not None else 0.0
            gateway_market_value = gateway.market_value if gateway is not None else 0.0
            market_value_diff = local_market_value - gateway_market_value
            if abs(market_value_diff) > self.cash_tolerance:
                diffs[f"{symbol}.market_value"] = market_value_diff
        return diffs

    def _record(
        self,
        status: ReconciliationStatus,
        *,
        startup: bool,
        cash_diff: float,
        position_diffs: dict[str, float],
        account_diffs: dict[str, float],
        position_value_diffs: dict[str, float],
        message: str,
    ) -> ReconciliationResult:
        result = ReconciliationResult(
            status=status,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            message=message,
            account_diffs=account_diffs,
            position_value_diffs=position_value_diffs,
        )
        self.journal.append(
            "reconciliation",
            {
                "startup": startup,
                "status": status.value,
                "cash_diff": cash_diff,
                "position_diffs": position_diffs,
                "account_diffs": account_diffs,
                "position_value_diffs": position_value_diffs,
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
        account_diffs: dict[str, float],
        position_value_diffs: dict[str, float],
        message: str,
    ) -> ReconciliationResult:
        self.store.set_engine_state(EngineState.HALT, message, updated_at=self.clock())
        return self._record(
            ReconciliationStatus.FAILED,
            startup=startup,
            cash_diff=cash_diff,
            position_diffs=position_diffs,
            account_diffs=account_diffs,
            position_value_diffs=position_value_diffs,
            message=message,
        )
