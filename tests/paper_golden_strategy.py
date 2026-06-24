from quant.core.contract import Bar, Context, StrategyBase


class GoldenPaperStrategy(StrategyBase):
    def on_init(self, ctx: Context) -> None:
        self.symbol = str(ctx.params["symbol"])
        self.target_qty = float(ctx.params["target_qty"])
        self.submitted = False

    def on_bar(self, ctx: Context, bar: Bar) -> None:
        if self.submitted or bar.symbol != self.symbol:
            return
        self.submitted = True
        ctx.set_target(self.symbol, self.target_qty)
