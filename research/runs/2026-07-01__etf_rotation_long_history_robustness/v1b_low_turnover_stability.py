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
ARTIFACT_PATH = RUN_DIR / "artifacts" / "v1b_low_turnover_stability.json"
DATA_ROOT = REPO_ROOT / "research/datasets/akshare_etf_rotation_510300_510500_20200101_20260630"
CONFIG_PATH = (
    REPO_ROOT
    / "research/imported/usage_records/2026-06-26__quant_usage_record/strategy_lab/"
    / "etf_regime_rotation_510300_510500.yaml"
)
INITIAL_CASH = 100_000.0


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


def equity_frame(equity: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(equity).copy()
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame["total_value"] = frame["total_value"].astype(float)
    frame["cash"] = frame["cash"].astype(float)
    frame["exposure"] = (frame["total_value"] - frame["cash"]) / frame["total_value"]
    return frame


def period_metrics(frame: pd.DataFrame) -> dict[str, float]:
    values = frame["total_value"]
    return {
        "return_pct": return_pct(values),
        "max_drawdown_pct": max_drawdown(values),
    }


def yearly_metrics(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for year, group in frame.groupby(frame["dt"].dt.year):
        if len(group) < 2:
            continue
        output[str(year)] = period_metrics(group)
    return output


def rolling_504_metrics(frame: pd.DataFrame) -> dict[str, float | int | None]:
    window = 504
    if len(frame) < window:
        return {
            "window_sessions": window,
            "windows": 0,
            "min_return_pct": None,
            "median_return_pct": None,
            "max_return_pct": None,
            "worst_max_drawdown_pct": None,
            "negative_return_windows": 0,
        }
    returns: list[float] = []
    drawdowns: list[float] = []
    for start in range(0, len(frame) - window + 1):
        group = frame.iloc[start : start + window]
        returns.append(return_pct(group["total_value"]))
        drawdowns.append(max_drawdown(group["total_value"]))
    return {
        "window_sessions": window,
        "windows": len(returns),
        "min_return_pct": round(min(returns), 4),
        "median_return_pct": round(median(returns), 4),
        "max_return_pct": round(max(returns), 4),
        "worst_max_drawdown_pct": round(min(drawdowns), 4),
        "negative_return_windows": sum(1 for item in returns if item < 0),
    }


def run_case(case: CaseSpec, slippage_bps: float) -> dict[str, object]:
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
    frame = equity_frame(result.equity)
    rejected = [order for order in result.orders if order.status == OrderStatus.REJECTED]
    trade_notional = sum(trade.qty * trade.price for trade in result.trades)
    rejects_by_reason: dict[str, int] = {}
    for order in rejected:
        reason = order.reject_reason or "unknown"
        rejects_by_reason[reason] = rejects_by_reason.get(reason, 0) + 1
    return {
        "case": case.case,
        "slippage_bps": slippage_bps,
        "params": params,
        "return_pct": return_pct(frame["total_value"]),
        "max_drawdown_pct": max_drawdown(frame["total_value"]),
        "orders": len(result.orders),
        "trades": len(result.trades),
        "rejected_orders": len(rejected),
        "rejects_by_reason": rejects_by_reason,
        "turnover_x_initial_cash": round(trade_notional / INITIAL_CASH, 4),
        "average_exposure_pct": pct(float(frame["exposure"].mean())),
        "days_exposure_below_5_pct": pct(float((frame["exposure"] < 0.05).mean())),
        "yearly": yearly_metrics(frame),
        "rolling_504_sessions": rolling_504_metrics(frame),
    }


def summarize_case(results: list[dict[str, object]]) -> dict[str, object]:
    by_slippage = {item["slippage_bps"]: item for item in results}
    zero = by_slippage[0.0]
    stress = by_slippage[20.0]
    yearly_20 = stress["yearly"]
    negative_years_20 = [
        year for year, metrics in yearly_20.items() if metrics["return_pct"] < 0
    ]
    return {
        "params": zero["params"],
        "return_0bps": zero["return_pct"],
        "max_drawdown_0bps": zero["max_drawdown_pct"],
        "return_20bps": stress["return_pct"],
        "max_drawdown_20bps": stress["max_drawdown_pct"],
        "orders_0bps": zero["orders"],
        "orders_20bps": stress["orders"],
        "turnover_0bps": zero["turnover_x_initial_cash"],
        "average_exposure_0bps": zero["average_exposure_pct"],
        "rejected_orders_0bps": zero["rejected_orders"],
        "rejected_orders_20bps": stress["rejected_orders"],
        "negative_years_20bps": negative_years_20,
        "rolling_504_20bps": stress["rolling_504_sessions"],
    }


def main() -> None:
    cases = [
        CaseSpec(
            case=(
                f"exposure_{str(exposure).replace('.', '_')}"
                f"_hold_{hold}_buffer_{str(buffer).replace('.', '_')}"
            ),
            target_exposure_pct=exposure,
            min_hold_days=hold,
            score_buffer=buffer,
        )
        for exposure in [0.5, 0.6, 0.7]
        for hold in [30, 40, 50]
        for buffer in [0.03, 0.05, 0.07]
    ]
    raw_results = [
        run_case(case, slippage_bps)
        for case in cases
        for slippage_bps in [0.0, 20.0]
    ]
    by_case: dict[str, list[dict[str, object]]] = {}
    for item in raw_results:
        by_case.setdefault(str(item["case"]), []).append(item)
    case_summary = {case: summarize_case(results) for case, results in by_case.items()}

    equal_weight_60_return = 23.7395
    equal_weight_60_max_dd = -28.4041
    for summary in case_summary.values():
        summary["passes_return_gate_vs_equal_weight_60"] = (
            summary["return_0bps"] >= equal_weight_60_return
        )
        summary["passes_drawdown_gate_vs_equal_weight_60"] = (
            summary["max_drawdown_0bps"] >= equal_weight_60_max_dd
        )
        summary["passes_20bps_positive_gate"] = summary["return_20bps"] > 0
        summary["passes_no_reject_gate"] = (
            summary["rejected_orders_0bps"] == 0 and summary["rejected_orders_20bps"] == 0
        )
        rolling = summary["rolling_504_20bps"]
        summary["passes_rolling_20bps_gate"] = rolling["negative_return_windows"] == 0
        summary["passes_all_hard_gates"] = all(
            [
                summary["passes_return_gate_vs_equal_weight_60"],
                summary["passes_drawdown_gate_vs_equal_weight_60"],
                summary["passes_20bps_positive_gate"],
                summary["passes_no_reject_gate"],
            ]
        )

    passing_hard = [
        case for case, summary in case_summary.items() if summary["passes_all_hard_gates"]
    ]
    passing_full_stability = [
        case
        for case, summary in case_summary.items()
        if summary["passes_all_hard_gates"] and summary["passes_rolling_20bps_gate"]
    ]
    best_20bps = max(
        case_summary.items(),
        key=lambda item: (item[1]["return_20bps"], item[1]["max_drawdown_20bps"]),
    )
    worst_20bps_return = min(item["return_20bps"] for item in case_summary.values())
    output = {
        "status": "research_only",
        "not_trading_permission": True,
        "experiment": "v1b_low_turnover_parameter_neighborhood_stability",
        "data_root": str(DATA_ROOT.relative_to(REPO_ROOT)),
        "strategy": "etf_regime_rotation_v1b_low_turnover",
        "method_note": (
            "3x3x3 neighborhood around target_exposure_pct=0.6, min_hold_days=40, "
            "score_buffer=0.05; trend_window=60 and momentum_window=20 fixed; "
            "slippage 0 bps and 20 bps; session-fixed execution."
        ),
        "comparison_gate": {
            "equal_weight_fixed_60_return_pct": equal_weight_60_return,
            "equal_weight_fixed_60_max_drawdown_pct": equal_weight_60_max_dd,
            "hard_gates": [
                "0 bps return >= equal-weight fixed 60%",
                "0 bps max drawdown no worse than equal-weight fixed 60%",
                "20 bps return > 0",
                "rejected orders = 0",
            ],
            "stability_warning_gate": "20 bps 504-session rolling windows should not be negative",
        },
        "cases": [case.__dict__ for case in cases],
        "case_summary": case_summary,
        "passing_hard_gate_cases": passing_hard,
        "passing_full_stability_cases": passing_full_stability,
        "best_20bps_case": {"case": best_20bps[0], **best_20bps[1]},
        "neighborhood_health": {
            "total_cases": len(cases),
            "hard_gate_pass_count": len(passing_hard),
            "full_stability_pass_count": len(passing_full_stability),
            "worst_20bps_return_pct": worst_20bps_return,
            "all_cases_20bps_positive": worst_20bps_return > 0,
        },
        "raw_results": raw_results,
        "decision": "HOLD_FOR_REGIME_STABILITY_REVIEW",
    }
    ARTIFACT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["neighborhood_health"], ensure_ascii=False, indent=2))
    print(json.dumps(output["best_20bps_case"], ensure_ascii=False, indent=2)[:1200])


if __name__ == "__main__":
    main()
