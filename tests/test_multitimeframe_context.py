from datetime import datetime
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from quant.backtest.engine import BacktestEngine
from quant.core.config import RiskConfig, StrategyConfig
from quant.core.contract import StrategyBase
from quant.data.service import DataService


UTC = ZoneInfo("UTC")


def test_4h_context_cannot_see_daily_bar_until_daily_close(
    monkeypatch,
    tmp_path: Path,
) -> None:
    observations: list[dict[str, object]] = []
    strategy_module = ModuleType("tests.no_lookahead_daily_strategy")

    class NoLookaheadDailyStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            history = ctx.history(self.symbol, n=5, freq="1d", adjust="raw")
            max_history_dt = None if history.empty else history["dt"].max().to_pydatetime()
            visible_daily = ctx.get_visible_bar_time("1d")
            daily_bar = ctx.get_bar(self.symbol, freq="1d")
            observations.append(
                {
                    "now": ctx.now,
                    "primary_dt": bar.dt,
                    "history_max": max_history_dt,
                    "visible_daily": visible_daily,
                    "daily_bar_dt": None if daily_bar is None else daily_bar.dt,
                }
            )
            if not history.empty and max_history_dt > ctx.now:
                raise AssertionError("history returned a future daily bar")
            if not self.sent and not history.empty and float(history.iloc[-1]["close"]) >= 150:
                self.sent = True
                ctx.set_target(self.symbol, 1)

    strategy_module.NoLookaheadDailyStrategy = NoLookaheadDailyStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.no_lookahead_daily_strategy" else None,
    )

    config = StrategyConfig.model_validate(
        {
            "id": "no_lookahead_daily",
            "class": "tests.no_lookahead_daily_strategy:NoLookaheadDailyStrategy",
            "version": "1.0",
            "universe": ["AAA-USD"],
            "frequencies": {"primary": "4h", "history": ["4h", "1d"]},
            "calendar": "continuous_24x7",
            "params": {"symbol": "AAA-USD"},
            "risk": RiskConfig(
                max_order_value=10_000,
                max_position_value=10_000,
                max_gross_exposure_pct=1,
            ),
            "runtime_mode": "backtest",
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_multitimeframe_dataset(tmp_path)),
        initial_cash=1_000,
    ).run()

    before_daily_close = [
        row
        for row in observations
        if row["now"] < datetime(2026, 1, 3, 0, tzinfo=UTC)
    ]
    assert before_daily_close
    assert all(
        row["visible_daily"] == datetime(2026, 1, 2, 0, tzinfo=UTC)
        for row in before_daily_close
    )
    assert all(row["history_max"] <= row["now"] for row in observations)
    assert all(row["daily_bar_dt"] == row["visible_daily"] for row in observations)
    assert observations[-2]["visible_daily"] == datetime(2026, 1, 3, 0, tzinfo=UTC)
    assert len(result.orders) == 1
    assert result.orders[0].created_at == datetime(2026, 1, 3, 4, tzinfo=UTC)
    assert not [
        trade for trade in result.trades if trade.dt < datetime(2026, 1, 3, 0, tzinfo=UTC)
    ]


def test_context_history_raises_for_unconfigured_frequency(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_module = ModuleType("tests.unsupported_history_frequency_strategy")

    class UnsupportedHistoryFrequencyStrategy(StrategyBase):
        def on_bar(self, ctx, bar) -> None:
            ctx.history("AAA-USD", n=1, freq="2h", adjust="raw")

    strategy_module.UnsupportedHistoryFrequencyStrategy = UnsupportedHistoryFrequencyStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module
            if name == "tests.unsupported_history_frequency_strategy"
            else None
        ),
    )
    config = StrategyConfig.model_validate(
        {
            "id": "unsupported_history_frequency",
            "class": (
                "tests.unsupported_history_frequency_strategy:"
                "UnsupportedHistoryFrequencyStrategy"
            ),
            "version": "1.0",
            "universe": ["AAA-USD"],
            "frequencies": {"primary": "4h", "history": ["4h", "1d"]},
            "calendar": "continuous_24x7",
            "params": {},
            "runtime_mode": "backtest",
        }
    )

    with pytest.raises(ValueError, match="2h"):
        BacktestEngine(
            config=config,
            data=DataService(_write_multitimeframe_dataset(tmp_path)),
            initial_cash=1_000,
        ).run()


def _write_multitimeframe_dataset(tmp_path: Path) -> Path:
    data_root = tmp_path / "multitimeframe"
    data_root.mkdir()
    _bars_4h().to_csv(data_root / "bars_4h.csv", index=False)
    _bars_1d().to_csv(data_root / "bars_1d.csv", index=False)
    _instruments().to_csv(data_root / "instruments.csv", index=False)
    (data_root / "dataset_manifest.yaml").write_text(
        """
dataset_id: no_lookahead_fixture
source: test_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2026-01-02T00:00:00Z"
  end: "2026-01-03T04:00:00Z"
symbols:
  - symbol: AAA-USD
    type: spot
    exchange: TEST
    active_from: "2026-01-02T00:00:00Z"
    active_to: null
    qty_step: 1
    lot_size: 1
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: PT4H
    coverage:
      start: "2026-01-02T00:00:00Z"
      end: "2026-01-03T04:00:00Z"
    construction: source
  - freq: 1d
    file: bars_1d.csv
    expected_interval: P1D
    coverage:
      start: "2026-01-02T00:00:00Z"
      end: "2026-01-03T00:00:00Z"
    construction: aggregate_from_4h
    aggregation:
      source_freq: 4h
      boundary_timezone: UTC
""",
        encoding="utf-8",
    )
    return data_root


def _bars_4h() -> pd.DataFrame:
    rows = []
    for index, dt in enumerate(
        [
            "2026-01-02T00:00:00+00:00",
            "2026-01-02T04:00:00+00:00",
            "2026-01-02T08:00:00+00:00",
            "2026-01-02T12:00:00+00:00",
            "2026-01-02T16:00:00+00:00",
            "2026-01-02T20:00:00+00:00",
            "2026-01-03T00:00:00+00:00",
            "2026-01-03T04:00:00+00:00",
        ]
    ):
        close = 100.0 + index
        rows.append(_bar_row("AAA-USD", dt, open_price=close - 1, close_price=close))
    return pd.DataFrame(rows)


def _bars_1d() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _bar_row(
                "AAA-USD",
                "2026-01-02T00:00:00+00:00",
                open_price=95,
                close_price=100,
            ),
            _bar_row(
                "AAA-USD",
                "2026-01-03T00:00:00+00:00",
                open_price=100,
                close_price=200,
            ),
        ]
    )


def _bar_row(
    symbol: str,
    dt: str,
    *,
    open_price: float,
    close_price: float,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "dt": dt,
        "open": open_price,
        "high": max(open_price, close_price) + 1,
        "low": min(open_price, close_price) - 1,
        "close": close_price,
        "volume": 1_000,
        "amount": close_price * 1_000,
        "pre_close": open_price,
        "limit_up": "",
        "limit_down": "",
        "suspended": False,
        "data_status": "ok",
        "source": "test",
        "updated_at": "2026-01-03T05:00:00+00:00",
    }


def _instruments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA-USD",
                "name": "AAA",
                "type": "spot",
                "exchange": "TEST",
                "list_date": "2026-01-01",
                "delist_date": "",
                "lot_size": 1,
                "qty_step": 1,
                "tick_size": 0.01,
                "t_plus": 0,
                "status": "active",
            }
        ]
    )
