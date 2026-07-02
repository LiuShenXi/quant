from __future__ import annotations

from pathlib import Path

from quant.backtest.engine import BacktestEngine
from quant.core.config import StrategyConfig
from quant.data.service import DataService


def test_crypto_trend_breadth_sets_top2_targets_after_closed_daily_and_4h_bars(
    tmp_path: Path,
) -> None:
    config = StrategyConfig.model_validate(
        {
            "id": "crypto_trend_breadth_top2_v1",
            "class": "strategies.crypto_trend_breadth:CryptoTrendBreadthTop2",
            "version": "1.0.0",
            "universe": ["BTC", "ETH", "SOL"],
            "frequencies": {"primary": "4h", "history": ["4h", "1d"]},
            "calendar": "continuous_24x7",
            "account": {
                "currency": "USDT",
                "settlement": "t0",
                "allow_fractional": True,
            },
            "params": {
                "rank_symbols": ["BTC", "ETH", "SOL"],
                "breadth_min_uptrends": 2,
                "top_n": 2,
                "target_weights": {"leader": 0.60, "runner_up": 0.40},
                "trend_freq": "1d",
                "rebalance_freq": "4h",
                "trend_ema_days": 2,
                "trend_ema_slope_days": 1,
                "rank_lookback_bars": 2,
            },
            "risk": {
                "max_order_value": {
                    "value": 1_000,
                    "unit": "quote_currency",
                    "currency": "USDT",
                },
                "max_position_value": {
                    "value": 1_000,
                    "unit": "quote_currency",
                    "currency": "USDT",
                },
                "max_gross_exposure_pct": 1.0,
                "max_orders_per_minute": 20,
            },
            "costs": {
                "model": "bps",
                "preset": "synthetic_smoke",
                "fee_bps": 10,
                "slippage_bps": 20,
            },
            "runtime_mode": "backtest",
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(_write_crypto_research_smoke_dataset(tmp_path)),
        initial_cash=1_000,
    ).run()

    target_events = [
        event for event in result.events if event.event_type == "target_intent"
    ]
    top2_targets = [
        event
        for event in target_events
        if event.payload.get("source_bar_timestamp") == "2026-01-02T04:00:00+00:00"
        and event.payload.get("target_weight", 0.0) > 0.0
    ]
    flat_targets = [
        event
        for event in target_events
        if event.payload.get("source_bar_timestamp") == "2026-01-02T04:00:00+00:00"
        and event.payload.get("target_weight") == 0.0
    ]

    assert [(event.symbol, event.payload["target_weight"]) for event in top2_targets] == [
        ("ETH", 0.6),
        ("SOL", 0.4),
    ]
    assert [(event.symbol, event.payload["target_weight"]) for event in flat_targets] == [
        ("BTC", 0.0),
    ]
    assert all(
        event.timestamp.isoformat() >= event.payload["source_bar_timestamp"]
        for event in top2_targets
    )
    assert any(trade.symbol == "ETH" for trade in result.trades)
    assert any(trade.symbol == "SOL" for trade in result.trades)


def _write_crypto_research_smoke_dataset(tmp_path: Path) -> Path:
    data_root = tmp_path / "crypto_research_smoke"
    data_root.mkdir()
    (data_root / "bars_1d.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,pre_close,limit_up,limit_down,suspended,data_status,source,updated_at",
                "BTC,2025-12-31T00:00:00+00:00,90,91,89,90,1000,90000,90,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "ETH,2025-12-31T00:00:00+00:00,45,46,44,45,1000,45000,45,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "SOL,2025-12-31T00:00:00+00:00,18,19,17,18,1000,18000,18,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "BTC,2026-01-01T00:00:00+00:00,100,101,99,100,1000,100000,100,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "ETH,2026-01-01T00:00:00+00:00,50,51,49,50,1000,50000,50,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "SOL,2026-01-01T00:00:00+00:00,20,21,19,20,1000,20000,20,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "BTC,2026-01-02T00:00:00+00:00,100,111,99,110,1000,110000,100,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "ETH,2026-01-02T00:00:00+00:00,50,56,49,55,1000,55000,50,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
                "SOL,2026-01-02T00:00:00+00:00,20,23,19,22,1000,22000,20,,,False,ok,synthetic,2026-01-02T00:00:00+00:00",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "bars_4h.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,pre_close,limit_up,limit_down,suspended,data_status,source,updated_at",
                "BTC,2026-01-02T00:00:00+00:00,100,101,99,100,1000,100000,100,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "ETH,2026-01-02T00:00:00+00:00,50,51,49,50,1000,50000,50,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "SOL,2026-01-02T00:00:00+00:00,20,21,19,20,1000,20000,20,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "BTC,2026-01-02T04:00:00+00:00,100,103,99,102,1000,102000,100,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "ETH,2026-01-02T04:00:00+00:00,50,57,49,56,1000,56000,50,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "SOL,2026-01-02T04:00:00+00:00,20,23,19,22,1000,22000,20,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "BTC,2026-01-02T08:00:00+00:00,102,103,101,102,1000,102000,102,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "ETH,2026-01-02T08:00:00+00:00,56,57,55,56,1000,56000,56,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
                "SOL,2026-01-02T08:00:00+00:00,22,23,21,22,1000,22000,22,,,False,ok,synthetic,2026-01-02T12:00:00+00:00",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "instruments.csv").write_text(
        "\n".join(
            [
                "symbol,name,type,exchange,list_date,delist_date,lot_size,qty_step,tick_size,t_plus,status,allow_fractional",
                "BTC,BTC,crypto_spot,SYNTHETIC,2025-12-31,,0.000001,0.000001,0.01,0,active,true",
                "ETH,ETH,crypto_spot,SYNTHETIC,2025-12-31,,0.000001,0.000001,0.01,0,active,true",
                "SOL,SOL,crypto_spot,SYNTHETIC,2025-12-31,,0.000001,0.000001,0.01,0,active,true",
            ]
        ),
        encoding="utf-8",
    )
    (data_root / "dataset_manifest.yaml").write_text(
        """
dataset_id: crypto_research_smoke
source: synthetic_strategy_contract_fixture
timezone: UTC
calendar: continuous_24x7
quote_currency: USDT
coverage:
  start: "2025-12-31T00:00:00Z"
  end: "2026-01-02T08:00:00Z"
symbols:
  - symbol: BTC
    type: crypto_spot
    exchange: SYNTHETIC
    active_from: "2025-12-31T00:00:00Z"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
  - symbol: ETH
    type: crypto_spot
    exchange: SYNTHETIC
    active_from: "2025-12-31T00:00:00Z"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
  - symbol: SOL
    type: crypto_spot
    exchange: SYNTHETIC
    active_from: "2025-12-31T00:00:00Z"
    active_to: null
    qty_step: 0.000001
    lot_size: 0.000001
    t_plus: 0
frequencies:
  - freq: 4h
    file: bars_4h.csv
    expected_interval: PT4H
    coverage:
      start: "2026-01-02T00:00:00Z"
      end: "2026-01-02T08:00:00Z"
    construction: synthetic_source
  - freq: 1d
    file: bars_1d.csv
    expected_interval: P1D
    coverage:
      start: "2025-12-31T00:00:00Z"
      end: "2026-01-02T00:00:00Z"
    construction: synthetic_daily_close
""",
        encoding="utf-8",
    )
    return data_root
