from __future__ import annotations


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
