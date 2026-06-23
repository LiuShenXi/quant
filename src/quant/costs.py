from dataclasses import dataclass

from quant.core.contract import OrderSide


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
