from pathlib import Path

import pytest

import quant.costs as costs
from quant.backtest.engine import BacktestEngine
from quant.core.config import CostConfig, RiskConfig, load_strategy_config
from quant.core.contract import OrderSide
from quant.costs import CostModel
from quant.data.service import DataService


def test_bps_cost_model_applies_fee_and_slippage_independently() -> None:
    model = costs.BpsCostModel(fee_bps=10, slippage_bps=20, preset="baseline")

    breakdown = model.calculate_breakdown(OrderSide.BUY, qty=2, price=10_000)

    assert breakdown.fee == 20.0
    assert breakdown.estimated_slippage_cost == 40.0
    assert breakdown.total_cost == 60.0
    assert model.calculate(OrderSide.BUY, qty=2, price=10_000) == 20.0


@pytest.mark.parametrize("preset", ["mild", "baseline", "stress"])
def test_bps_cost_preset_and_totals_are_available_for_reports(preset: str) -> None:
    config = _active_sample_config().model_copy(
        update={
            "costs": CostConfig(
                model="bps",
                preset=preset,
                fee_bps=10,
                slippage_bps=20,
            ),
            "risk": RiskConfig(
                max_order_value=500_000,
                max_position_value=500_000,
                max_gross_exposure_pct=10,
            ),
        }
    )

    result = BacktestEngine(
        config=config,
        data=DataService(Path("data_sample")),
        initial_cash=100_000,
    ).run()

    trade = result.trades[0]
    notional = trade.qty * trade.price
    expected_fee = round(notional * 10 / 10_000, 2)
    expected_slippage = round(notional * 20 / 10_000, 2)
    fill_event = next(event for event in result.events if event.event_type == "fill")

    assert result.cost_report_inputs == {
        "model": "bps",
        "preset": preset,
        "fee_bps": 10.0,
        "slippage_bps": 20.0,
        "slippage_accounting": "separate_estimate_not_fill_price",
        "total_fee": expected_fee,
        "estimated_slippage_cost": expected_slippage,
    }
    assert trade.commission == expected_fee
    assert fill_event.payload["commission"] == expected_fee
    assert fill_event.payload["estimated_slippage_cost"] == expected_slippage
    assert fill_event.payload["slippage_accounting"] == "separate_estimate_not_fill_price"
    assert trade.price == fill_event.payload["price"]


def test_legacy_a_share_cost_model_still_returns_existing_fee_values() -> None:
    model = CostModel(
        commission_rate=0.00025,
        commission_min=5,
        stamp_tax=0.001,
        transfer_fee=0.00002,
    )

    assert model.calculate(OrderSide.BUY, qty=1000, price=3.0) == 5.06
    assert model.calculate(OrderSide.SELL, qty=10_000, price=10.0) == 127.0


def _active_sample_config():
    return load_strategy_config(Path("config/strategies/dual_ma_510300.yaml")).model_copy(
        update={"params": {"symbol": "510300.SH", "fast": 1, "slow": 2, "target_qty": 10000}}
    )
