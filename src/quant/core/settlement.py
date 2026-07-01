from dataclasses import dataclass

from quant.core.contract import Instrument
from quant.core.sizing import round_qty_down


@dataclass(frozen=True)
class SettlementRules:
    currency: str = "CNY"
    settlement: str = "t1"
    allow_fractional: bool = False

    def round_qty(self, raw_qty: float, instrument: Instrument) -> float:
        return float(
            round_qty_down(
                qty=raw_qty,
                lot_size=float(instrument.lot_size),
                qty_step=float(instrument.qty_step),
                allow_fractional=self.allow_fractional
                and _instrument_allows_fractional(instrument),
            )
        )

    def sellable_lag_bars(self, instrument: Instrument | None = None) -> int:
        configured_lag = _settlement_to_lag(self.settlement)
        instrument_lag = int(instrument.t_plus) if instrument is not None else configured_lag
        return max(configured_lag, instrument_lag)


def _settlement_to_lag(value: str) -> int:
    normalized = value.strip().lower()
    if normalized.startswith("t+"):
        return int(normalized[2:])
    if normalized.startswith("t"):
        return int(normalized[1:] or 0)
    raise ValueError(f"unsupported settlement rule {value!r}")


def _instrument_allows_fractional(instrument: Instrument) -> bool:
    return instrument.allow_fractional
