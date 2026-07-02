from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant.core.contract import Bar, Context, StrategyBase


@dataclass(frozen=True)
class _RankedSymbol:
    symbol: str
    total_return: float
    realized_volatility: float
    universe_order: int


class CryptoTrendBreadthTop2(StrategyBase):
    def on_init(self, ctx: Context) -> None:
        params = ctx.params
        self.rank_symbols = list(params["rank_symbols"])
        self.breadth_min_uptrends = int(params.get("breadth_min_uptrends", 2))
        self.top_n = int(params.get("top_n", 2))
        weights = dict(params["target_weights"])
        self.target_weights = [
            float(weights["leader"]),
            float(weights["runner_up"]),
        ]
        self.trend_freq = str(params.get("trend_freq", "1d"))
        self.rebalance_freq = str(params.get("rebalance_freq", "4h"))
        self.trend_ema_days = int(params.get("trend_ema_days", 50))
        self.trend_ema_slope_days = int(params.get("trend_ema_slope_days", 10))
        self.rank_lookback_bars = int(params.get("rank_lookback_bars", 20))
        self._last_rebalance_date = None

    def on_bar(self, ctx: Context, bar: Bar) -> None:
        if bar.freq != self.rebalance_freq:
            return
        if bar.symbol != self.rank_symbols[0]:
            return
        if self._last_rebalance_date == ctx.now.date():
            return

        uptrend_count = sum(1 for symbol in self.rank_symbols if self._is_uptrend(ctx, symbol))
        if uptrend_count < self.breadth_min_uptrends:
            self._set_flat_targets(ctx)
            self._last_rebalance_date = ctx.now.date()
            return

        ranked = self._rank_symbols(ctx)
        if len(ranked) < self.top_n:
            return

        selected = ranked[: self.top_n]
        selected_symbols = {item.symbol for item in selected}
        for item, weight in zip(selected, self.target_weights, strict=False):
            ctx.set_target_weight(item.symbol, weight)
        for symbol in self.rank_symbols:
            if symbol not in selected_symbols:
                ctx.set_target_weight(symbol, 0.0)
        self._last_rebalance_date = ctx.now.date()

    def _is_uptrend(self, ctx: Context, symbol: str) -> bool:
        rows_needed = self.trend_ema_days + self.trend_ema_slope_days
        history = ctx.history(symbol, n=rows_needed, freq=self.trend_freq, adjust="raw")
        if len(history) < rows_needed:
            return False

        close = history["close"].astype(float)
        ema = close.ewm(span=self.trend_ema_days, adjust=False).mean()
        return bool(
            close.iloc[-1] > ema.iloc[-1]
            and ema.iloc[-1] > ema.iloc[-1 - self.trend_ema_slope_days]
        )

    def _rank_symbols(self, ctx: Context) -> list[_RankedSymbol]:
        ranked: list[_RankedSymbol] = []
        for universe_order, symbol in enumerate(self.rank_symbols):
            history = ctx.history(
                symbol,
                n=self.rank_lookback_bars,
                freq=self.rebalance_freq,
                adjust="raw",
            )
            if len(history) < self.rank_lookback_bars:
                continue
            closes = history["close"].astype(float)
            start = float(closes.iloc[0])
            end = float(closes.iloc[-1])
            if start <= 0:
                continue
            ranked.append(
                _RankedSymbol(
                    symbol=symbol,
                    total_return=end / start - 1.0,
                    realized_volatility=_realized_volatility(closes),
                    universe_order=universe_order,
                )
            )
        return sorted(
            ranked,
            key=lambda item: (-item.total_return, item.realized_volatility, item.universe_order),
        )

    def _set_flat_targets(self, ctx: Context) -> None:
        for symbol in self.rank_symbols:
            ctx.set_target_weight(symbol, 0.0)


def _realized_volatility(closes: pd.Series) -> float:
    returns = closes.pct_change().dropna()
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0))
