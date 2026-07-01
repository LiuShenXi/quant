from dataclasses import dataclass
from typing import Any

from quant.core.contract import OrderSide


SLIPPAGE_ACCOUNTING_SEPARATE_ESTIMATE = "separate_estimate_not_fill_price"


@dataclass(frozen=True)
class CostBreakdown:
    fee: float
    estimated_slippage_cost: float = 0.0
    model: str = "legacy_a_share"
    preset: str | None = None
    fee_bps: float | None = None
    slippage_bps: float | None = None
    slippage_accounting: str | None = None

    @property
    def total_cost(self) -> float:
        return round(self.fee + self.estimated_slippage_cost, 2)

    def fill_event_fields(self) -> dict[str, object]:
        if self.model != "bps":
            return {}
        return {
            "fee": self.fee,
            "fee_bps": self.fee_bps,
            "estimated_slippage_cost": self.estimated_slippage_cost,
            "slippage_bps": self.slippage_bps,
            "slippage_accounting": self.slippage_accounting,
            "cost_preset": self.preset,
        }


@dataclass(frozen=True)
class CostModel:
    commission_rate: float
    commission_min: float
    stamp_tax: float
    transfer_fee: float

    def calculate(self, side: OrderSide, qty: float, price: float) -> float:
        value = qty * price
        commission = max(value * self.commission_rate, self.commission_min)
        stamp = value * self.stamp_tax if side == OrderSide.SELL else 0.0
        transfer = value * self.transfer_fee
        return round(commission + stamp + transfer, 2)

    def calculate_breakdown(self, side: OrderSide, qty: float, price: float) -> CostBreakdown:
        return CostBreakdown(fee=self.calculate(side, qty, price))

    def report_inputs(self) -> dict[str, object]:
        return {
            "model": "legacy_a_share",
            "preset": None,
            "commission_rate": self.commission_rate,
            "commission_min": self.commission_min,
            "stamp_tax": self.stamp_tax,
            "transfer_fee": self.transfer_fee,
        }


@dataclass(frozen=True)
class BpsCostModel:
    fee_bps: float
    slippage_bps: float
    preset: str | None = None

    def __post_init__(self) -> None:
        if self.fee_bps < 0:
            raise ValueError("fee_bps must be non-negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative")

    def calculate(self, side: OrderSide, qty: float, price: float) -> float:
        return self.calculate_breakdown(side, qty, price).fee

    def calculate_breakdown(self, side: OrderSide, qty: float, price: float) -> CostBreakdown:
        notional = qty * price
        # Slippage is a separate research estimate. It does not alter fill price,
        # Trade.commission, portfolio cash, or gateway-compatible trade records.
        return CostBreakdown(
            fee=round(notional * self.fee_bps / 10_000, 2),
            estimated_slippage_cost=round(notional * self.slippage_bps / 10_000, 2),
            model="bps",
            preset=self.preset,
            fee_bps=float(self.fee_bps),
            slippage_bps=float(self.slippage_bps),
            slippage_accounting=SLIPPAGE_ACCOUNTING_SEPARATE_ESTIMATE,
        )

    def report_inputs(self) -> dict[str, object]:
        return {
            "model": "bps",
            "preset": self.preset,
            "fee_bps": float(self.fee_bps),
            "slippage_bps": float(self.slippage_bps),
            "slippage_accounting": SLIPPAGE_ACCOUNTING_SEPARATE_ESTIMATE,
        }


def cost_model_from_config(config: Any) -> CostModel | BpsCostModel:
    if getattr(config, "model", None) == "bps":
        fee_bps = _required_number(config, "fee_bps")
        slippage_bps = _required_number(config, "slippage_bps")
        return BpsCostModel(
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            preset=getattr(config, "preset", None),
        )
    return CostModel(
        commission_rate=0.00025,
        commission_min=5,
        stamp_tax=0,
        transfer_fee=0,
    )


def _required_number(config: Any, field_name: str) -> float:
    value = getattr(config, field_name, None)
    if value is None:
        raise ValueError(f"costs.{field_name} is required for bps cost model")
    return float(value)
