from datetime import date
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from quant.backtest.engine import BacktestEngine
from quant.core.config import AccountConfig, FrequencyConfig, RiskConfig, load_strategy_config
from quant.core.contract import Instrument, OrderSide, StrategyBase, Trade
from quant.core.portfolio import Portfolio
from quant.data.service import DataService


SH = ZoneInfo("Asia/Shanghai")


def test_manifest_backed_spot_account_uses_configured_quote_currency(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_module = ModuleType("tests.spot_noop_strategy")

    class NoopStrategy(StrategyBase):
        pass

    strategy_module.NoopStrategy = NoopStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: strategy_module if name == "tests.spot_noop_strategy" else None,
    )

    config = _spot_config(class_path="tests.spot_noop_strategy:NoopStrategy")
    engine = BacktestEngine(
        config=config,
        data=DataService(_write_spot_manifest_data(tmp_path)),
        initial_cash=1_000,
    )

    assert engine.portfolio.account({}).currency == "USD"


def test_fractional_t0_spot_can_be_marked_and_sold_on_next_bar(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_module = ModuleType("tests.fractional_t0_round_trip_strategy")
    observations: list[dict[str, object]] = []

    class FractionalRoundTripStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.calls = 0

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.symbol:
                return
            self.calls += 1
            position = ctx.get_position(self.symbol)
            account = ctx.get_account()
            observations.append(
                {
                    "dt": ctx.now.isoformat(),
                    "qty": position.qty,
                    "sellable": position.sellable,
                    "market_value": position.market_value,
                    "currency": account.currency,
                }
            )
            if self.calls == 1:
                ctx.set_target_value(self.symbol, 0.10)
            elif self.calls == 2:
                ctx.set_target(self.symbol, 0.0)

    strategy_module.FractionalRoundTripStrategy = FractionalRoundTripStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module if name == "tests.fractional_t0_round_trip_strategy" else None
        ),
    )

    result = BacktestEngine(
        config=_spot_config(
            class_path="tests.fractional_t0_round_trip_strategy:FractionalRoundTripStrategy"
        ),
        data=DataService(_write_spot_manifest_data(tmp_path)),
        initial_cash=1_000,
    ).run()

    assert [trade.side for trade in result.trades] == [OrderSide.BUY, OrderSide.SELL]
    assert [trade.qty for trade in result.trades] == [pytest.approx(0.001), pytest.approx(0.001)]
    assert result.trades[0].dt.isoformat() == "2024-01-02T10:00:00+08:00"
    assert result.trades[1].dt.isoformat() == "2024-01-02T11:00:00+08:00"
    assert observations[1]["qty"] == pytest.approx(0.001)
    assert observations[1]["market_value"] == pytest.approx(0.105)
    assert observations[1]["currency"] == "USD"
    assert observations[2]["qty"] == pytest.approx(0.0)


def test_manifest_backed_symbol_without_fractional_permission_does_not_fill_fractional_qty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_module = ModuleType("tests.no_fractional_permission_strategy")

    class NoFractionalPermissionStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.symbol = ctx.params["symbol"]
            self.sent = False

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol == self.symbol and not self.sent:
                self.sent = True
                ctx.set_target_value(self.symbol, 0.10)

    strategy_module.NoFractionalPermissionStrategy = NoFractionalPermissionStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module if name == "tests.no_fractional_permission_strategy" else None
        ),
    )

    result = BacktestEngine(
        config=_spot_config(
            class_path="tests.no_fractional_permission_strategy:NoFractionalPermissionStrategy"
        ),
        data=DataService(
            _write_spot_manifest_data(
                tmp_path,
                instrument_allow_fractional=False,
            )
        ),
        initial_cash=1_000,
    ).run()

    assert result.orders == []
    assert result.trades == []


def test_a_share_lot_rounding_and_t1_sellable_rollover_stay_legacy_compatible() -> None:
    from quant.core.settlement import SettlementRules

    instrument = Instrument(
        symbol="510300.SH",
        name="ETF",
        type="etf",
        exchange="SH",
        list_date=date(2020, 1, 1),
        delist_date=None,
        lot_size=100,
        qty_step=100,
        tick_size=0.001,
        t_plus=1,
        status="active",
    )
    rules = SettlementRules()

    assert rules.round_qty(255.9, instrument) == 200

    portfolio = Portfolio(account_id="backtest", initial_cash=100_000)
    portfolio.apply_trade(
        Trade(
            trade_id="T-1",
            order_id="O-1",
            strategy_id="legacy",
            account_id="backtest",
            symbol="510300.SH",
            side=OrderSide.BUY,
            qty=200,
            price=3.0,
            commission=5.0,
            dt=pd.Timestamp("2024-01-03T15:00:00+08:00").to_pydatetime(),
        )
    )

    assert portfolio.account({"510300.SH": 3.0}).currency == "CNY"
    assert portfolio.position("510300.SH", mark_price=3.0).sellable == 0

    portfolio.mark_new_day()

    assert portfolio.position("510300.SH", mark_price=3.0).sellable == 200


def test_t_plus_two_buy_releases_sellable_after_two_day_advances() -> None:
    instrument = Instrument(
        symbol="LOCKED.SPOT",
        name="Locked Spot",
        type="spot",
        exchange="TEST",
        list_date=date(2020, 1, 1),
        delist_date=None,
        lot_size=1,
        qty_step=1,
        tick_size=0.01,
        t_plus=2,
        status="active",
    )
    portfolio = Portfolio(account_id="backtest", initial_cash=100_000)
    portfolio.apply_trade(
        Trade(
            trade_id="T-1",
            order_id="O-1",
            strategy_id="settlement",
            account_id="backtest",
            symbol="LOCKED.SPOT",
            side=OrderSide.BUY,
            qty=10,
            price=10.0,
            commission=0.0,
            dt=pd.Timestamp("2024-01-03T15:00:00+08:00").to_pydatetime(),
        ),
        instrument=instrument,
    )

    portfolio.mark_new_day()

    assert portfolio.position("LOCKED.SPOT", mark_price=10.0).sellable == 0

    portfolio.mark_new_day()

    assert portfolio.position("LOCKED.SPOT", mark_price=10.0).sellable == 10


def _spot_config(*, class_path: str):
    return load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={
            "class_path": class_path,
            "universe": ["AAA-USD"],
            "frequencies": FrequencyConfig(primary="1h", history=["1h"]),
            "account": AccountConfig(currency="USD", settlement="t0", allow_fractional=True),
            "params": {"symbol": "AAA-USD"},
            "risk": RiskConfig(
                max_order_value=1_000,
                max_position_value=1_000,
                max_gross_exposure_pct=1.0,
                max_orders_per_minute=10,
            ),
        }
    )


def _write_spot_manifest_data(
    tmp_path: Path,
    *,
    instrument_allow_fractional: bool = True,
) -> Path:
    data_root = tmp_path / "spot_manifest_data"
    data_root.mkdir()
    pd.DataFrame(
        [
            _bar("2024-01-02T09:00:00+08:00", open_price=100.0, close_price=100.0),
            _bar("2024-01-02T10:00:00+08:00", open_price=100.0, close_price=105.0),
            _bar("2024-01-02T11:00:00+08:00", open_price=105.0, close_price=105.0),
        ]
    ).to_csv(data_root / "bars_1h.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "AAA-USD",
                "name": "AAA Spot",
                "type": "spot",
                "exchange": "TEST",
                "list_date": "2024-01-01",
                "delist_date": "",
                "lot_size": 1,
                "qty_step": 1,
                "tick_size": 0.01,
                "t_plus": 0,
                "status": "active",
                "allow_fractional": instrument_allow_fractional,
            }
        ]
    ).to_csv(data_root / "instruments.csv", index=False)
    (data_root / "dataset_manifest.yaml").write_text(
        """
dataset_id: spot_fractional_fixture
source: test_fixture
timezone: Asia/Shanghai
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: "2024-01-02T09:00:00+08:00"
  end: "2024-01-02T11:00:00+08:00"
symbols:
  - symbol: AAA-USD
    type: spot
    exchange: TEST
    active_from: "2024-01-02T09:00:00+08:00"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 1h
    file: bars_1h.csv
    expected_interval: PT1H
    coverage:
      start: "2024-01-02T09:00:00+08:00"
      end: "2024-01-02T11:00:00+08:00"
    construction: source
""",
        encoding="utf-8",
    )
    return data_root


def _bar(dt: str, *, open_price: float, close_price: float) -> dict[str, object]:
    return {
        "symbol": "AAA-USD",
        "dt": dt,
        "open": open_price,
        "high": max(open_price, close_price),
        "low": min(open_price, close_price),
        "close": close_price,
        "volume": 100.0,
        "amount": close_price * 100.0,
        "pre_close": open_price,
        "limit_up": open_price * 2,
        "limit_down": open_price * 0.5,
        "suspended": False,
        "data_status": "ok",
        "source": "test",
        "updated_at": dt,
    }
