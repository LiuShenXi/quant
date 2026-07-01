from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any


PortfolioStopEventSink = Callable[["PortfolioStopEvent"], None]


@dataclass(frozen=True)
class PortfolioStopConfig:
    trailing_drawdown_pct: float
    cooldown: timedelta
    defensive_target: Mapping[str, Any] = field(default_factory=lambda: {"mode": "flat"})
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.trailing_drawdown_pct <= 0:
            raise ValueError("trailing_drawdown_pct must be positive")
        if self.cooldown < timedelta(0):
            raise ValueError("cooldown must be non-negative")


@dataclass(frozen=True)
class PortfolioStopState:
    cycle_state: str = "ACTIVE"
    cycle_peak_value: float | None = None
    stop_triggered_at: datetime | None = None
    cooldown_until: datetime | None = None
    defensive_target: Mapping[str, Any] | None = None
    last_reentry_check: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class PortfolioStopDecision:
    cycle_state: str
    triggered: bool = False
    defensive_target: Mapping[str, Any] | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PortfolioStopEvent:
    event_type: str
    timestamp: datetime
    risk_rule_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReentryPredicateValue:
    name: str
    source_component: str
    freq: str
    visible_bar_dt: datetime
    construction: str
    value: Any
    fully_closed: bool = True

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_component": self.source_component,
            "freq": self.freq,
            "visible_bar_dt": self.visible_bar_dt.isoformat(),
            "construction": self.construction,
            "value": self.value,
            "fully_closed": self.fully_closed,
        }


@dataclass(frozen=True)
class ReentryPredicateInput:
    predicate_id: str
    as_of: datetime
    decision_time: datetime
    required_cooling_until: datetime | None
    result: bool
    inputs: list[ReentryPredicateValue]


class PortfolioStop:
    def __init__(
        self,
        config: PortfolioStopConfig,
        *,
        event_sink: PortfolioStopEventSink | None = None,
    ) -> None:
        self.config = config
        self.state = PortfolioStopState()
        self._event_sink = event_sink

    def set_event_sink(self, event_sink: PortfolioStopEventSink | None) -> None:
        self._event_sink = event_sink

    def on_equity(self, timestamp: datetime, equity_value: float) -> PortfolioStopDecision:
        if not self.config.enabled:
            return PortfolioStopDecision(cycle_state=self.state.cycle_state)

        if self.state.cycle_state != "ACTIVE":
            return PortfolioStopDecision(
                cycle_state=self.state.cycle_state,
                defensive_target=self.state.defensive_target,
                reason="portfolio_stop_active",
            )

        peak = self.state.cycle_peak_value
        if peak is None or equity_value > peak:
            peak = equity_value
            self.state = replace(self.state, cycle_peak_value=peak)

        if peak is None or peak <= 0:
            return PortfolioStopDecision(cycle_state=self.state.cycle_state)

        drawdown_pct = (peak - equity_value) / peak
        if drawdown_pct < self.config.trailing_drawdown_pct:
            return PortfolioStopDecision(cycle_state=self.state.cycle_state)

        defensive_target = dict(self.config.defensive_target)
        cooldown_until = timestamp + self.config.cooldown
        self.state = replace(
            self.state,
            cycle_state="COOLDOWN",
            stop_triggered_at=timestamp,
            cooldown_until=cooldown_until,
            defensive_target=defensive_target,
        )
        payload = {
            "cycle_state": "COOLDOWN",
            "cycle_peak_value": peak,
            "equity_value": equity_value,
            "drawdown_pct": drawdown_pct,
            "trailing_drawdown_pct": self.config.trailing_drawdown_pct,
            "stop_triggered_at": timestamp.isoformat(),
            "cooldown_until": cooldown_until.isoformat(),
            "defensive_target": defensive_target,
        }
        self._emit(
            "risk_portfolio_stop",
            timestamp=timestamp,
            risk_rule_id="portfolio_stop_drawdown",
            payload=payload,
        )
        self._emit(
            "risk_cooldown_start",
            timestamp=timestamp,
            risk_rule_id="portfolio_stop_cooldown",
            payload=payload,
        )
        return PortfolioStopDecision(
            cycle_state="COOLDOWN",
            triggered=True,
            defensive_target=defensive_target,
            reason="drawdown_breach",
        )

    def allows_opening_exposure(self, timestamp: datetime) -> bool:
        if self.state.cycle_state == "ACTIVE":
            return True
        if self.state.cooldown_until is not None and timestamp < self.state.cooldown_until:
            return False
        return False

    def opening_exposure_reject_reason(self, timestamp: datetime) -> str:
        if self.state.cooldown_until is not None and timestamp < self.state.cooldown_until:
            return "portfolio stop cooldown blocks new opening exposure"
        return "portfolio stop requires audited re-entry before opening exposure"

    def check_reentry(self, predicate_input: ReentryPredicateInput | None) -> bool:
        if self.state.cycle_state == "ACTIVE":
            return True

        if predicate_input is None:
            self._record_reentry_check(
                timestamp=self._fallback_reentry_timestamp(),
                predicate_id=None,
                as_of=None,
                decision_time=None,
                required_cooling_until=self.state.cooldown_until,
                inputs=[],
                result=False,
                reason="missing_input",
            )
            return False

        reason = self._reentry_rejection_reason(predicate_input)
        result = reason is None and bool(predicate_input.result)
        if reason is None:
            reason = "predicate_true" if result else "predicate_false"

        if result:
            self.state = replace(
                self.state,
                cycle_state="ACTIVE",
                cycle_peak_value=None,
                stop_triggered_at=None,
                cooldown_until=None,
                defensive_target=None,
            )
        else:
            self.state = replace(self.state, cycle_state=self._blocked_reentry_state(predicate_input))

        self._record_reentry_check(
            timestamp=predicate_input.decision_time,
            predicate_id=predicate_input.predicate_id,
            as_of=predicate_input.as_of,
            decision_time=predicate_input.decision_time,
            required_cooling_until=predicate_input.required_cooling_until,
            inputs=[value.metadata() for value in predicate_input.inputs],
            result=result,
            reason=reason,
        )
        if result:
            self._emit(
                "risk_portfolio_reentry",
                timestamp=predicate_input.decision_time,
                risk_rule_id="portfolio_stop_reentry",
                payload={
                    "predicate_id": predicate_input.predicate_id,
                    "result": True,
                    "reason": reason,
                },
            )
        return result

    def _reentry_rejection_reason(self, predicate_input: ReentryPredicateInput) -> str | None:
        if (
            self.state.cooldown_until is not None
            and predicate_input.decision_time < self.state.cooldown_until
        ):
            return "cooldown_active"
        if predicate_input.as_of > predicate_input.decision_time:
            return "future_as_of"
        if (
            predicate_input.required_cooling_until is not None
            and self.state.cooldown_until is not None
            and predicate_input.required_cooling_until != self.state.cooldown_until
        ):
            return "cooldown_mismatch"
        if not predicate_input.inputs:
            return "missing_inputs"
        for value in predicate_input.inputs:
            if not value.name or not value.source_component or not value.freq or not value.construction:
                return "incomplete_input_metadata"
            if value.visible_bar_dt > predicate_input.decision_time:
                return "future_visible_bar"
            if not value.fully_closed:
                return "not_fully_closed"
        return None

    def _blocked_reentry_state(self, predicate_input: ReentryPredicateInput) -> str:
        if (
            self.state.cooldown_until is not None
            and predicate_input.decision_time < self.state.cooldown_until
        ):
            return "COOLDOWN"
        return "STOPPED"

    def _record_reentry_check(
        self,
        *,
        timestamp: datetime,
        predicate_id: str | None,
        as_of: datetime | None,
        decision_time: datetime | None,
        required_cooling_until: datetime | None,
        inputs: list[dict[str, Any]],
        result: bool,
        reason: str,
    ) -> None:
        payload = {
            "predicate_id": predicate_id,
            "as_of": as_of.isoformat() if as_of is not None else None,
            "decision_time": decision_time.isoformat() if decision_time is not None else None,
            "required_cooling_until": (
                required_cooling_until.isoformat()
                if required_cooling_until is not None
                else None
            ),
            "inputs": inputs,
            "result": result,
            "reason": reason,
        }
        self.state = replace(self.state, last_reentry_check=payload)
        self._emit(
            "risk_reentry_check",
            timestamp=timestamp,
            risk_rule_id="portfolio_stop_reentry",
            payload=payload,
        )

    def _fallback_reentry_timestamp(self) -> datetime:
        if self.state.cooldown_until is not None:
            return self.state.cooldown_until
        if self.state.stop_triggered_at is not None:
            return self.state.stop_triggered_at
        raise ValueError("missing re-entry input requires an initialized stop timestamp")

    def _emit(
        self,
        event_type: str,
        *,
        timestamp: datetime,
        risk_rule_id: str,
        payload: dict[str, Any],
    ) -> None:
        if self._event_sink is None:
            return
        self._event_sink(
            PortfolioStopEvent(
                event_type=event_type,
                timestamp=timestamp,
                risk_rule_id=risk_rule_id,
                payload=payload,
            )
        )


def portfolio_stop_config_from_mapping(raw: object) -> PortfolioStopConfig | None:
    if raw is None:
        return None
    if isinstance(raw, PortfolioStopConfig):
        return raw if raw.enabled else None
    if not isinstance(raw, Mapping):
        raise ValueError("portfolio_stop config must be a mapping")

    enabled = bool(raw.get("enabled", True))
    if not enabled:
        return None
    if "trailing_drawdown_pct" not in raw:
        raise ValueError("portfolio_stop.trailing_drawdown_pct is required")
    cooldown = _cooldown_from_mapping(raw)
    defensive_target = raw.get("defensive_target", {"mode": "flat"})
    if not isinstance(defensive_target, Mapping):
        raise ValueError("portfolio_stop.defensive_target must be a mapping")
    return PortfolioStopConfig(
        trailing_drawdown_pct=float(raw["trailing_drawdown_pct"]),
        cooldown=cooldown,
        defensive_target=dict(defensive_target),
        enabled=enabled,
    )


def _cooldown_from_mapping(raw: Mapping[str, Any]) -> timedelta:
    value = raw.get("cooldown")
    if isinstance(value, timedelta):
        return value
    if "cooldown_hours" in raw:
        return timedelta(hours=float(raw["cooldown_hours"]))
    if "cooldown_days" in raw:
        return timedelta(days=float(raw["cooldown_days"]))
    raise ValueError("portfolio_stop cooldown, cooldown_hours, or cooldown_days is required")
