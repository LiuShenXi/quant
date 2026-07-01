from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import pandas as pd
from v1b_regime_failure_review import (
    DATA_ROOT,
    INITIAL_CASH,
    REPO_ROOT,
    SYMBOLS,
    CaseSpec,
    max_drawdown,
    period_metrics,
    return_pct,
    run_strategy,
)

RUN_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = RUN_DIR / "artifacts" / "v1b_fixed_exposure_substitution.json"


def load_fixed_exposure_equity(exposures: list[float]) -> pd.DataFrame:
    bars = pd.read_csv(DATA_ROOT / "bars_1d.csv", parse_dates=["dt"])
    wide = bars.pivot(index="dt", columns="symbol", values="close").sort_index()
    relative = wide[SYMBOLS] / wide[SYMBOLS].iloc[0]
    output = pd.DataFrame({"dt": pd.to_datetime(wide.index).normalize()})
    for exposure in exposures:
        exposure_label = int(exposure * 100)
        output[f"fixed_{exposure_label}_equal_weight"] = (
            INITIAL_CASH * ((1 - exposure) + exposure * relative.mean(axis=1))
        ).to_numpy()
        for symbol in SYMBOLS:
            symbol_label = symbol.replace(".", "_")
            output[f"fixed_{exposure_label}_{symbol_label}"] = (
                INITIAL_CASH * ((1 - exposure) + exposure * relative[symbol])
            ).to_numpy()
    output["cash"] = INITIAL_CASH
    return output.reset_index(drop=True)


def rolling_stats(frame: pd.DataFrame, column: str, window: int = 504) -> dict[str, float | int]:
    returns: list[float] = []
    drawdowns: list[float] = []
    for start in range(0, len(frame) - window + 1):
        group = frame.iloc[start : start + window]
        returns.append(return_pct(group[column]))
        drawdowns.append(max_drawdown(group[column]))
    return {
        "window_sessions": window,
        "windows": len(returns),
        "negative_windows": sum(1 for item in returns if item < 0),
        "min_return_pct": round(min(returns), 4),
        "median_return_pct": round(median(returns), 4),
        "max_return_pct": round(max(returns), 4),
        "worst_drawdown_pct": round(min(drawdowns), 4),
        "median_drawdown_pct": round(median(drawdowns), 4),
    }


def dominates(candidate: dict[str, object], strategy: dict[str, object]) -> bool:
    return (
        candidate["return_pct"] >= strategy["return_pct"]
        and candidate["max_drawdown_pct"] >= strategy["max_drawdown_pct"]
        and candidate["rolling_504_sessions"]["negative_windows"]
        <= strategy["rolling_504_sessions"]["negative_windows"]
    )


def score_return_per_drawdown(metrics: dict[str, object]) -> float | None:
    max_dd = abs(metrics["max_drawdown_pct"])
    if max_dd == 0:
        return None
    return round(metrics["return_pct"] / max_dd, 4)


def build_equity_frame() -> pd.DataFrame:
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
    frame = load_fixed_exposure_equity([0.4, 0.5, 0.6])
    run_meta: list[dict[str, object]] = []
    for case in cases:
        strategy_frame, meta = run_strategy(case, slippage_bps=20.0)
        frame = frame.merge(strategy_frame, on="dt", how="inner")
        run_meta.append(meta)
    return frame, run_meta


def main() -> None:
    frame, run_meta = build_equity_frame()
    strategy_columns = [
        "v1b_center_0_6_hold_40_buffer_0_05_20bps",
        "v1b_best20_0_7_hold_30_buffer_0_07_20bps",
    ]
    benchmark_columns = [column for column in frame.columns if column.startswith("fixed_")]
    columns = [*strategy_columns, *benchmark_columns, "cash"]
    metrics = {
        column: {
            **period_metrics(frame, column),
            "rolling_504_sessions": rolling_stats(frame, column),
        }
        for column in columns
    }
    for values in metrics.values():
        values["return_per_abs_max_drawdown"] = score_return_per_drawdown(values)

    substitution_tests: dict[str, dict[str, object]] = {}
    for strategy in strategy_columns:
        strategy_metrics = metrics[strategy]
        dominating = [
            column
            for column in benchmark_columns
            if dominates(metrics[column], strategy_metrics)
        ]
        higher_return_lower_dd = [
            column
            for column in benchmark_columns
            if metrics[column]["return_pct"] >= strategy_metrics["return_pct"]
            and metrics[column]["max_drawdown_pct"] >= strategy_metrics["max_drawdown_pct"]
        ]
        fewer_negative_windows = [
            column
            for column in benchmark_columns
            if metrics[column]["rolling_504_sessions"]["negative_windows"]
            <= strategy_metrics["rolling_504_sessions"]["negative_windows"]
        ]
        substitution_tests[strategy] = {
            "dominating_fixed_exposure_cases": dominating,
            "higher_return_and_lower_max_dd_cases": higher_return_lower_dd,
            "fewer_or_equal_negative_window_cases": fewer_negative_windows,
            "best_return_per_drawdown_fixed_case": max(
                benchmark_columns,
                key=lambda column: metrics[column]["return_per_abs_max_drawdown"] or -999,
            ),
        }

    output = {
        "status": "research_only",
        "not_trading_permission": True,
        "experiment": "v1b_fixed_exposure_substitution",
        "method_note": (
            "Compare v1b drawdown-control representatives against simple fixed 40/50/60% "
            "close-to-close exposure curves. No parameter search."
        ),
        "data_root": str(DATA_ROOT.relative_to(REPO_ROOT)),
        "strategy_cases": run_meta,
        "metrics": metrics,
        "substitution_tests": substitution_tests,
        "decision": "HOLD_FOR_PATH_SMOOTHING_UTILITY_REVIEW",
    }
    ARTIFACT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["substitution_tests"], ensure_ascii=False, indent=2))
    selected = [
        "v1b_center_0_6_hold_40_buffer_0_05_20bps",
        "v1b_best20_0_7_hold_30_buffer_0_07_20bps",
        "fixed_40_equal_weight",
        "fixed_50_equal_weight",
        "fixed_60_equal_weight",
    ]
    print(json.dumps({key: metrics[key] for key in selected}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
