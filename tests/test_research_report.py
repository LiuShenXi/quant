from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from quant.backtest.engine import BacktestResult
from quant.backtest.events import JournalEvent
from quant.backtest.results import write_result
from quant.core.config import StrategyConfig
from quant.core.contract import OrderSide, Trade


def test_write_result_exports_research_report_json_and_markdown_safety(tmp_path: Path) -> None:
    output_dir, _ = _write_report(tmp_path)

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "report.md").read_text(encoding="utf-8")

    assert report["not_trading_permission"] is True
    assert set(report) >= {
        "not_trading_permission",
        "strategy_metrics",
        "turnover",
        "rebalance_count",
        "time_in_cash",
        "time_by_symbol",
        "total_fee",
        "estimated_slippage_cost",
        "cost_preset_name",
        "benchmarks",
        "data_period",
        "timezone",
        "risk_stop_summary",
    }
    assert "research-only" in markdown.lower()
    assert "not trading permission" in markdown.lower()
    prohibited_approval_wording = [
        "approved for paper",
        "approved for live",
        "real-money approval",
        "permission to trade",
        "can trade",
        "可以 paper",
        "可以 live",
        "可以真钱",
    ]
    for phrase in prohibited_approval_wording:
        assert phrase not in markdown.lower()


def test_write_result_generates_configured_benchmarks_and_copies_manifest(
    tmp_path: Path,
) -> None:
    output_dir, data_root = _write_report(tmp_path)

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))

    assert (output_dir / "dataset_manifest.yaml").read_text(
        encoding="utf-8"
    ) == (data_root / "dataset_manifest.yaml").read_text(encoding="utf-8")
    assert set(report["benchmarks"]) == {
        "cash_usd",
        "hold_aaa",
        "equal_weight_pair",
    }
    assert "BTC" not in json.dumps(report["benchmarks"])
    assert "ETH" not in json.dumps(report["benchmarks"])
    assert "SOL" not in json.dumps(report["benchmarks"])
    assert report["benchmarks"]["cash_usd"]["type"] == "cash"
    assert report["benchmarks"]["cash_usd"]["metrics"]["return_pct"] == 0.0
    assert report["benchmarks"]["hold_aaa"]["type"] == "single_asset_buy_hold"
    assert report["benchmarks"]["hold_aaa"]["metrics"]["return_pct"] == 21.0
    assert report["benchmarks"]["equal_weight_pair"]["type"] == "equal_weight_buy_hold"
    assert report["benchmarks"]["equal_weight_pair"]["metrics"]["return_pct"] == 20.5


def test_write_result_includes_costs_risk_stop_and_activity_summary(
    tmp_path: Path,
) -> None:
    output_dir, _ = _write_report(tmp_path)

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))

    assert report["cost_preset_name"] == "baseline"
    assert report["total_fee"] == 12.34
    assert report["estimated_slippage_cost"] == 23.45
    assert report["risk_stop_summary"] == {
        "triggered_events": 1,
        "latest_state": "COOLDOWN",
        "latest_reason": "drawdown_breach",
    }
    assert report["turnover"] == 1550.0
    assert report["rebalance_count"] == 2
    assert report["time_in_cash"] == 2 / 3
    assert report["time_by_symbol"] == {"AAA": 1.0}


def _write_report(tmp_path: Path) -> tuple[Path, Path]:
    data_root = _write_dataset(tmp_path / "data")
    output_dir = tmp_path / "out"
    write_result(
        _result(),
        output_dir=output_dir,
        config=_config(),
        data_root=data_root,
    )
    return output_dir, data_root


def _config() -> StrategyConfig:
    return StrategyConfig.model_validate(
        {
            "id": "generic_research_report",
            "class": "strategies.example:ExampleStrategy",
            "version": "1.0.0",
            "universe": ["AAA", "BBB"],
            "frequencies": {"primary": "1d"},
            "calendar": "continuous_24x7",
            "account": {
                "currency": "USD",
                "settlement": "t0",
                "allow_fractional": True,
            },
            "params": {},
            "risk": {},
            "costs": {
                "model": "bps",
                "preset": "baseline",
                "fee_bps": 10,
                "slippage_bps": 20,
            },
            "benchmarks": [
                {"id": "cash_usd", "type": "cash"},
                {
                    "id": "hold_aaa",
                    "type": "single_asset_buy_hold",
                    "symbol": "AAA",
                },
                {
                    "id": "equal_weight_pair",
                    "type": "equal_weight_buy_hold",
                    "symbols": ["AAA", "BBB"],
                },
            ],
            "runtime_mode": "backtest",
        }
    )


def _result() -> BacktestResult:
    return BacktestResult(
        orders=[],
        trades=[
            Trade(
                trade_id="T-1",
                order_id="O-1",
                strategy_id="generic_research_report",
                account_id="backtest",
                symbol="AAA",
                side=OrderSide.BUY,
                qty=10,
                price=100,
                commission=5,
                dt=_dt("2026-01-02T00:00:00+00:00"),
            ),
            Trade(
                trade_id="T-2",
                order_id="O-2",
                strategy_id="generic_research_report",
                account_id="backtest",
                symbol="AAA",
                side=OrderSide.SELL,
                qty=5,
                price=110,
                commission=7.34,
                dt=_dt("2026-01-03T00:00:00+00:00"),
            ),
        ],
        equity=[
            {
                "dt": "2026-01-01T00:00:00+00:00",
                "total_value": 100_000.0,
                "cash": 100_000.0,
            },
            {
                "dt": "2026-01-02T00:00:00+00:00",
                "total_value": 105_000.0,
                "cash": 20_000.0,
            },
            {
                "dt": "2026-01-03T00:00:00+00:00",
                "total_value": 110_000.0,
                "cash": 110_000.0,
            },
        ],
        events=[
            JournalEvent(
                run_id="generic_research_report",
                seq=1,
                event_type="rebalance_decision",
                timestamp=_dt("2026-01-02T00:00:00+00:00"),
                source_component="backtest.engine",
                strategy_id="generic_research_report",
                account_id="backtest",
                symbol="AAA",
                payload={"action": "submit_order"},
            ),
            JournalEvent(
                run_id="generic_research_report",
                seq=2,
                event_type="rebalance_decision",
                timestamp=_dt("2026-01-03T00:00:00+00:00"),
                source_component="backtest.engine",
                strategy_id="generic_research_report",
                account_id="backtest",
                symbol="AAA",
                payload={"action": "submit_order"},
            ),
            JournalEvent(
                run_id="generic_research_report",
                seq=3,
                event_type="risk_portfolio_stop",
                timestamp=_dt("2026-01-03T00:00:00+00:00"),
                source_component="quant.risk.portfolio_stop",
                strategy_id="generic_research_report",
                account_id="backtest",
                risk_rule_id="portfolio_stop_drawdown",
                payload={
                    "cycle_state": "COOLDOWN",
                    "reason": "drawdown_breach",
                },
            ),
        ],
        cost_report_inputs={
            "model": "bps",
            "preset": "baseline",
            "fee_bps": 10.0,
            "slippage_bps": 20.0,
            "total_fee": 12.34,
            "estimated_slippage_cost": 23.45,
        },
    )


def _write_dataset(data_root: Path) -> Path:
    data_root.mkdir()
    (data_root / "dataset_manifest.yaml").write_text(
        """dataset_id: generic_report_dataset
source: synthetic
timezone: UTC
calendar: continuous_24x7
quote_currency: USD
coverage:
  start: 2026-01-01T00:00:00+00:00
  end: 2026-01-03T00:00:00+00:00
symbols:
  - symbol: AAA
    type: synthetic
    exchange: TEST
    active_from: 2026-01-01T00:00:00+00:00
    qty_step: 1
    lot_size: 1
    t_plus: 0
  - symbol: BBB
    type: synthetic
    exchange: TEST
    active_from: 2026-01-01T00:00:00+00:00
    qty_step: 1
    lot_size: 1
    t_plus: 0
frequencies:
  - freq: 1d
    file: bars_1d.csv
    expected_interval: 1d
    coverage:
      start: 2026-01-01T00:00:00+00:00
      end: 2026-01-03T00:00:00+00:00
    construction: synthetic
""",
        encoding="utf-8",
    )
    (data_root / "bars_1d.csv").write_text(
        "\n".join(
            [
                "symbol,dt,open,high,low,close,volume,amount,data_status",
                "AAA,2026-01-01T00:00:00+00:00,100,100,100,100,1,100,ok",
                "AAA,2026-01-02T00:00:00+00:00,110,110,110,110,1,110,ok",
                "AAA,2026-01-03T00:00:00+00:00,121,121,121,121,1,121,ok",
                "BBB,2026-01-01T00:00:00+00:00,50,50,50,50,1,50,ok",
                "BBB,2026-01-02T00:00:00+00:00,40,40,40,40,1,40,ok",
                "BBB,2026-01-03T00:00:00+00:00,60,60,60,60,1,60,ok",
            ]
        ),
        encoding="utf-8",
    )
    return data_root


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(ZoneInfo("UTC"))
