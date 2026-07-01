from __future__ import annotations

import math


def split_qty_by_order_value(
    *,
    qty: float,
    price: float,
    max_order_value: float | None,
) -> list[float]:
    if qty <= 0:
        return []
    if price <= 0:
        return [qty]
    if max_order_value is None or max_order_value <= 0:
        return [qty]

    max_qty = (max_order_value / price) * (1 - 1e-12)
    if max_qty <= 0 or qty <= max_qty:
        return [qty]

    chunks: list[float] = []
    remaining = qty
    while remaining > max_qty:
        chunks.append(max_qty)
        remaining -= max_qty
    if remaining > 0:
        chunks.append(remaining)
    return chunks


def target_value_to_qty(
    *,
    target_value: float,
    price: float,
    lot_size: float,
    qty_step: float,
    allow_fractional: bool = False,
) -> float:
    if target_value <= 0:
        return 0.0
    if price <= 0:
        raise ValueError("valuation price must be positive")
    raw_qty = target_value / price
    return round_qty_down(
        qty=raw_qty,
        lot_size=lot_size,
        qty_step=qty_step,
        allow_fractional=allow_fractional,
    )


def round_qty_down(
    *,
    qty: float,
    lot_size: float,
    qty_step: float,
    allow_fractional: bool = False,
) -> float:
    if qty <= 0:
        return 0.0
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    if qty_step <= 0:
        raise ValueError("qty_step must be positive")
    if qty < lot_size:
        return 0.0

    step = float(qty_step)
    rounded = math.floor((qty + 1e-12) / step) * step
    if not allow_fractional:
        rounded = math.floor(rounded)
    return round(rounded, 12)
