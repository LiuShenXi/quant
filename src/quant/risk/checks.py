from datetime import time


def round_down_qty(qty: float, lot_size: int, qty_step: int) -> float:
    if qty < lot_size:
        return 0
    return qty - (qty % qty_step)


def is_cn_continuous_auction(value: time) -> bool:
    return time(9, 30) <= value <= time(11, 30) or time(13, 0) <= value <= time(14, 57)
