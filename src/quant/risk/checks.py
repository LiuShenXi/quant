def round_down_qty(qty: float, lot_size: int, qty_step: int) -> float:
    if qty < lot_size:
        return 0
    return qty - (qty % qty_step)
