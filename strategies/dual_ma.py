from quant.core.contract import Bar, StrategyBase


class DualMA(StrategyBase):
    def on_init(self, ctx) -> None:
        self.symbol = ctx.params["symbol"]
        self.fast = int(ctx.params["fast"])
        self.slow = int(ctx.params["slow"])
        self.target_qty = float(ctx.params["target_qty"])

    def on_bar(self, ctx, bar: Bar) -> None:
        if bar.symbol != self.symbol:
            return
        close = ctx.history(self.symbol, self.slow + 1, fields=["close"])["close"]
        if len(close) <= self.slow:
            return
        ma_fast = close.tail(self.fast).mean()
        ma_slow = close.tail(self.slow).mean()
        position = ctx.get_position(self.symbol)
        if ma_fast > ma_slow and position.qty == 0:
            ctx.set_target(self.symbol, self.target_qty)
        elif ma_fast < ma_slow and position.qty > 0:
            ctx.set_target(self.symbol, 0)
