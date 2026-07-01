from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import pandas as pd

from quant.backtest.engine import BacktestEngine
from quant.backtest.matcher import Matcher, MatchResult
from quant.core.config import load_strategy_config
from quant.core.contract import OrderSide, OrderStatus
from quant.data.service import DataService

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = RUN_DIR / "artifacts" / "v1b_regime_failure_review.json"
DATA_ROOT = REPO_ROOT / "research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630"
CONFIG_PATH = (
    REPO_ROOT
    / "research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/"
    / "etf_regime_rotation_510300_510500.yaml"
)
INITIAL_CASH = 100_000.0
SYMBOLS = ["510300.SH", "510500.SH"]


@dataclass(frozen=True)
class CaseSpec:
    case: str
    target_exposure_pct: float
    min_hold_days: int
    score_buffer: float


class SlippageMatcher:
    def __init__(self, base: Matcher, slippage_bps: float) -> None:
        self.base = base
        self.slippage_bps = slippage_bps

    def match(self, order, bar) -> MatchResult:
        result = self.base.match(order, bar)
        if result.fill_price is None or result.filled_qty <= 0 or self.slippage_bps == 0:
            return result
        multiplier = (
            1 + self.slippage_bps / 10_000
            if order.side == OrderSide.BUY
            else 1 - self.slippage_bps / 10_000
        )
        return MatchResult(result.filled_qty, result.fill_price * multiplier, result.reason)


def pct(value: float) -> float:
    return round(value * 100, 4)


def max_drawdown(values: pd.Series) -> float:
    drawdown = values / values.cummax() - 1
    return pct(float(drawdown.min()))


def return_pct(values: pd.Series) -> float:
    return pct(float(values.iloc[-1] / values.iloc[0] - 1))


def period_metrics(frame: pd.DataFrame, column: str) -> dict[str, float]:
    values = frame[column]
    return {
        "return_pct": return_pct(values),
        "max_drawdown_pct": max_drawdown(values),
    }


def equity_frame(equity: list[dict[str, object]], column: str) -> pd.DataFrame:
    frame = pd.DataFrame(equity).copy()
    frame["dt"] = pd.to_datetime(frame["dt"]).dt.normalize()
    frame[column] = frame["total_value"].astype(float)
    return frame[["dt", column]]


def run_strategy(case: CaseSpec, slippage_bps: float) -> tuple[pd.DataFrame, dict[str, object]]:
    base_config = load_strategy_config(CONFIG_PATH)
    params = {
        **base_config.params,
        "target_exposure_pct": case.target_exposure_pct,
        "min_hold_days": case.min_hold_days,
        "score_buffer": case.score_buffer,
    }
    config = base_config.model_copy(update={"params": params})
    engine = BacktestEngine(config=config, data=DataService(DATA_ROOT), initial_cash=INITIAL_CASH)
    engine.matcher = SlippageMatcher(engine.matcher, slippage_bps)
    result = engine.run()
    rejected = [order for order in result.orders if order.status == OrderStatus.REJECTED]
    trade_notional = sum(trade.qty * trade.price for trade in result.trades)
    return equity_frame(result.equity, case.case), {
        "case": case.case,
        "slippage_bps": slippage_bps,
        "params": params,
        "orders": len(result.orders),
        "trades": len(result.trades),
        "rejected_orders": len(rejected),
        "turnover_x_initial_cash": round(trade_notional / INITIAL_CASH, 4),
    }


def load_benchmark_equity() -> pd.DataFrame:
    bars = pd.read_csv(DATA_ROOT / "bars_1d.csv", parse_dates=["dt"])
    wide = bars.pivot(index="dt", columns="symbol", values="close").sort_index()
    relative = wide[SYMBOLS] / wide[SYMBOLS].iloc[0]
    output = pd.DataFrame({"dt": pd.to_datetime(wide.index).normalize()})
    output["fixed_60_equal_weight"] = (
        INITIAL_CASH * (0.4 + 0.6 * relative.mean(axis=1))
    ).to_numpy()
    for symbol in SYMBOLS:
        key = symbol.replace(".", "_")
        output[f"fixed_60_{key}"] = (
            INITIAL_CASH * (0.4 + 0.6 * relative[symbol])
        ).to_numpy()
    return output.reset_index(drop=True)


def yearly_table(frame: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, dict[str, float]]]:
    output: dict[str, dict[str, dict[str, float]]] = {}
    for year, group in frame.groupby(frame["dt"].dt.year):
        if len(group) < 2:
            continue
        output[str(year)] = {column: period_metrics(group, column) for column in columns}
    return output


def range_metrics(frame: pd.DataFrame, columns: list[str], start_year: int, end_year: int) -> dict:
    group = frame[(frame["dt"].dt.year >= start_year) & (frame["dt"].dt.year <= end_year)]
    return {column: period_metrics(group, column) for column in columns}


def rolling_returns(frame: pd.DataFrame, column: str, window: int) -> list[float]:
    returns: list[float] = []
    for start in range(0, len(frame) - window + 1):
        group = frame.iloc[start : start + window]
        returns.append(return_pct(group[column]))
    return returns


def rolling_comparison(
    frame: pd.DataFrame,
    strategy_column: str,
    benchmark_columns: list[str],
    window: int = 504,
) -> dict[str, object]:
    strategy_returns = rolling_returns(frame, strategy_column, window)
    benchmark_returns = {
        column: rolling_returns(frame, column, window) for column in benchmark_columns
    }
    output: dict[str, object] = {
        "window_sessions": window,
        "windows": len(strategy_returns),
        "strategy_min_return_pct": round(min(strategy_returns), 4),
        "strategy_median_return_pct": round(median(strategy_returns), 4),
        "strategy_max_return_pct": round(max(strategy_returns), 4),
        "strategy_negative_windows": sum(1 for item in strategy_returns if item < 0),
    }
    for column, returns in benchmark_returns.items():
        output[f"underperform_{column}_windows"] = sum(
            1 for strategy, benchmark in zip(strategy_returns, returns, strict=True)
            if strategy < benchmark
        )
        output[f"{column}_negative_windows"] = sum(1 for item in returns if item < 0)
        output[f"{column}_median_return_pct"] = round(median(returns), 4)
    return output


def yearly_relative_table(yearly: dict, strategy_columns: list[str], benchmark: str) -> dict:
    output: dict[str, dict[str, float]] = {}
    for year, row in yearly.items():
        output[year] = {
            strategy: round(row[strategy]["return_pct"] - row[benchmark]["return_pct"], 4)
            for strategy in strategy_columns
        }
    return output


def main() -> None:
    cases = [
        CaseSpec(
            case="v1b_center_0_6_hold_40_buffer_0_05_20bps",
            target_exposure_pct=0.6,
            min_hold_days=40,
            score_buffer=0.05,
        ),
        CaseSpec(
            case="v1b_best20_0_7_hold_30_buffer_0_07_20bps",
            target_exposure_pct=0.7,
            min_hold_days=30,
            score_buffer=0.07,
        ),
    ]
    benchmark = load_benchmark_equity()
    run_meta: list[dict[str, object]] = []
    frame = benchmark.copy()
    for case in cases:
        strategy_frame, meta = run_strategy(case, slippage_bps=20.0)
        frame = frame.merge(strategy_frame, on="dt", how="inner")
        run_meta.append(meta)

    strategy_columns = [case.case for case in cases]
    benchmark_columns = [
        "fixed_60_equal_weight",
        "fixed_60_510300_SH",
        "fixed_60_510500_SH",
    ]
    columns = [*strategy_columns, *benchmark_columns]
    yearly = yearly_table(frame, columns)
    output = {
        "status": "research_only",
        "not_trading_permission": True,
        "experiment": "v1b_regime_failure_review",
        "method_note": (
            "Compare representative v1b 20 bps strategy paths with close-to-close "
            "normalized fixed 60% benchmarks. No parameter search."
        ),
        "data_root": str(DATA_ROOT.relative_to(REPO_ROOT)),
        "strategy_cases": run_meta,
        "benchmarks": {
            "fixed_60_equal_weight": "40% cash + 30% 510300.SH + 30% 510500.SH",
            "fixed_60_510300_SH": "40% cash + 60% 510300.SH",
            "fixed_60_510500_SH": "40% cash + 60% 510500.SH",
        },
        "full_period": {column: period_metrics(frame, column) for column in columns},
        "yearly": yearly,
        "yearly_relative_to_fixed_60_equal_weight": yearly_relative_table(
            yearly,
            strategy_columns,
            "fixed_60_equal_weight",
        ),
        "failure_period_2021_2023": range_metrics(frame, columns, 2021, 2023),
        "rolling_504_sessions": {
            strategy: rolling_comparison(frame, strategy, benchmark_columns)
            for strategy in strategy_columns
        },
        "diagnosis": {
            "2021_2023_all_strategy_cases_negative": all(
                metrics["return_pct"] < 0
                for metrics in range_metrics(frame, strategy_columns, 2021, 2023).values()
            ),
            "2021_2023_equal_weight_negative": (
                range_metrics(frame, ["fixed_60_equal_weight"], 2021, 2023)[
                    "fixed_60_equal_weight"
                ]["return_pct"]
                < 0
            ),
            "interpretation": (
                "The weak segment overlaps with weak fixed 60% ETF benchmarks, but v1b still "
                "does not prove a stable timing edge because rolling windows frequently remain "
                "negative and underperform fixed equal-weight exposure."
            ),
        },
        "decision": "HOLD_FOR_DRAWDOWN_CONTROL_THESIS_REVIEW",
    }
    ARTIFACT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["failure_period_2021_2023"], ensure_ascii=False, indent=2))
    print(json.dumps(output["rolling_504_sessions"], ensure_ascii=False, indent=2)[:1800])


if __name__ == "__main__":
    main()
