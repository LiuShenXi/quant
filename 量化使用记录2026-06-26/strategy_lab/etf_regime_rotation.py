from __future__ import annotations

from datetime import date

from quant.core.contract import Bar, StrategyBase


class EtfRegimeRotation(StrategyBase):
    def on_init(self, ctx) -> None:
        self.symbols = list(ctx.params["symbols"])
        self.trend_window = int(ctx.params["trend_window"])
        self.momentum_window = int(ctx.params["momentum_window"])
        self.target_exposure_pct = float(ctx.params["target_exposure_pct"])
        self.min_hold_days = int(ctx.params.get("min_hold_days", 0))
        self.score_buffer = float(ctx.params.get("score_buffer", 0.0))
        if not 0 < self.target_exposure_pct <= 0.95:
            raise ValueError("target_exposure_pct must be in (0, 0.95]")
        if self.momentum_window <= 0 or self.trend_window <= 0:
            raise ValueError("windows must be positive")
        if self.momentum_window > self.trend_window:
            raise ValueError("momentum_window must be <= trend_window")

    def on_bar(self, ctx, bar: Bar) -> None:
        if bar.symbol != self.symbols[0]:
            return
        candidates = self._rank_candidates(ctx)
        current_symbol = self._current_symbol(ctx)
        if not candidates:
            if current_symbol is not None:
                self._set_targets(ctx, selected=None, target_qty=0)
                ctx.save_state("selected_symbol", None)
                ctx.save_state("last_switch_date", ctx.now.date().isoformat())
            return

        selected, selected_score = candidates[0]
        pending_selected = ctx.load_state("pending_selected_symbol", None)
        if current_symbol is None and pending_selected in self.symbols:
            ready_date = ctx.load_state("pending_ready_date", None)
            today = ctx.now.date().isoformat()
            if ready_date is None or ready_date == today:
                ctx.save_state("pending_ready_date", today)
                return
            selected = pending_selected
            target_qty = self._target_qty(ctx, selected)
            self._set_targets(ctx, selected=selected, target_qty=target_qty)
            ctx.save_state("selected_symbol", selected)
            ctx.save_state("pending_selected_symbol", None)
            ctx.save_state("pending_ready_date", None)
            ctx.save_state("last_switch_date", ctx.now.date().isoformat())
            return

        if current_symbol == selected:
            return
        if current_symbol is not None:
            current_score = self._score_for(candidates, current_symbol)
            if current_score is not None and selected_score - current_score < self.score_buffer:
                return
            if not self._can_switch(ctx):
                return
            self._set_targets(ctx, selected=None, target_qty=0)
            ctx.save_state("selected_symbol", None)
            ctx.save_state("pending_selected_symbol", selected)
            ctx.save_state("pending_ready_date", None)
            ctx.save_state("last_switch_date", ctx.now.date().isoformat())
            return

        target_qty = self._target_qty(ctx, selected)
        self._set_targets(ctx, selected=selected, target_qty=target_qty)
        ctx.save_state("selected_symbol", selected)
        ctx.save_state("pending_selected_symbol", None)
        ctx.save_state("last_switch_date", ctx.now.date().isoformat())

    def _rank_candidates(self, ctx) -> list[tuple[str, float]]:
        needed = self.trend_window + 1
        candidates: list[tuple[str, float]] = []
        for symbol in self.symbols:
            history = ctx.history(symbol, needed, fields=["close"])
            if len(history) < needed:
                return []
            closes = history["close"].astype(float)
            latest = float(closes.iloc[-1])
            trend_ma = float(closes.tail(self.trend_window).mean())
            if latest <= trend_ma:
                continue
            past = float(closes.iloc[-self.momentum_window])
            if past <= 0:
                continue
            candidates.append((symbol, latest / past - 1.0))
        return sorted(candidates, key=lambda item: item[1], reverse=True)

    def _current_symbol(self, ctx) -> str | None:
        for symbol in self.symbols:
            if ctx.get_position(symbol).qty > 0:
                return symbol
        saved = ctx.load_state("selected_symbol", None)
        return saved if saved in self.symbols else None

    def _score_for(self, candidates: list[tuple[str, float]], symbol: str) -> float | None:
        for candidate, score in candidates:
            if candidate == symbol:
                return score
        return None

    def _can_switch(self, ctx) -> bool:
        last_switch = ctx.load_state("last_switch_date", None)
        if not last_switch:
            return True
        return (ctx.now.date() - date.fromisoformat(last_switch)).days >= self.min_hold_days

    def _target_qty(self, ctx, symbol: str) -> float:
        account = ctx.get_account()
        price = float(ctx.history(symbol, 1, fields=["close"])["close"].iloc[-1])
        instrument = ctx.get_instrument(symbol)
        raw_qty = account.total_value * self.target_exposure_pct / price
        if raw_qty < instrument.lot_size:
            return 0
        return float(raw_qty - (raw_qty % instrument.qty_step))

    def _set_targets(self, ctx, *, selected: str | None, target_qty: float) -> None:
        for symbol in self.symbols:
            ctx.set_target(symbol, target_qty if symbol == selected else 0)
