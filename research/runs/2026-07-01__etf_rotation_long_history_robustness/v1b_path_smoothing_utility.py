from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import pandas as pd
from v1b_fixed_exposure_substitution import load_fixed_exposure_equity
from v1b_regime_failure_review import (
    DATA_ROOT,
    REPO_ROOT,
    CaseSpec,
    max_drawdown,
    period_metrics,
    return_pct,
    run_strategy,
)

RUN_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = RUN_DIR / "artifacts" / "v1b_path_smoothing_utility.json"


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


def rolling_window_metrics(
    frame: pd.DataFrame,
    column: str,
    window: int,
) -> dict[str, float | int]:
    returns: list[float] = []
    drawdowns: list[float] = []
    for start in range(0, len(frame) - window + 1):
        group = frame.iloc[start : start + window]
        returns.append(return_pct(group[column]))
        drawdowns.append(max_drawdown(group[column]))
    negative_windows = sum(1 for item in returns if item < 0)
    return {
        "window_sessions": window,
        "windows": len(returns),
        "negative_windows": negative_windows,
        "negative_window_pct": round(negative_windows / len(returns) * 100, 4),
        "min_return_pct": round(min(returns), 4),
        "median_return_pct": round(median(returns), 4),
        "max_return_pct": round(max(returns), 4),
        "worst_drawdown_pct": round(min(drawdowns), 4),
        "median_drawdown_pct": round(median(drawdowns), 4),
    }


def compare_to_benchmarks(
    metrics: dict[str, dict[str, float | int]],
    strategy: str,
    benchmarks: list[str],
) -> dict[str, dict[str, float | int | bool]]:
    output: dict[str, dict[str, float | int | bool]] = {}
    strategy_metrics = metrics[strategy]
    for benchmark in benchmarks:
        benchmark_metrics = metrics[benchmark]
        output[benchmark] = {
            "negative_window_reduction": (
                benchmark_metrics["negative_windows"] - strategy_metrics["negative_windows"]
            ),
            "median_return_gap_pct": round(
                strategy_metrics["median_return_pct"] - benchmark_metrics["median_return_pct"],
                4,
            ),
            "min_return_gap_pct": round(
                strategy_metrics["min_return_pct"] - benchmark_metrics["min_return_pct"],
                4,
            ),
            "median_drawdown_improvement_pct": round(
                strategy_metrics["median_drawdown_pct"] - benchmark_metrics["median_drawdown_pct"],
                4,
            ),
            "worst_drawdown_improvement_pct": round(
                strategy_metrics["worst_drawdown_pct"] - benchmark_metrics["worst_drawdown_pct"],
                4,
            ),
            "has_fewer_negative_windows": (
                strategy_metrics["negative_windows"] < benchmark_metrics["negative_windows"]
            ),
        }
    return output


def main() -> None:
    frame, run_meta = build_equity_frame()
    strategy_columns = [
        "v1b_center_0_6_hold_40_buffer_0_05_20bps",
        "v1b_best20_0_7_hold_30_buffer_0_07_20bps",
    ]
    benchmark_columns = [
        "fixed_40_equal_weight",
        "fixed_50_equal_weight",
        "fixed_60_equal_weight",
        "fixed_40_510500_SH",
        "fixed_50_510500_SH",
        "fixed_60_510500_SH",
    ]
    columns = [*strategy_columns, *benchmark_columns]
    full_period = {column: period_metrics(frame, column) for column in columns}
    windows = [252, 504, 756]
    rolling = {
        str(window): {
            "metrics": {
                column: rolling_window_metrics(frame, column, window) for column in columns
            },
            "comparisons": {
                strategy: compare_to_benchmarks(
                    {column: rolling_window_metrics(frame, column, window) for column in columns},
                    strategy,
                    benchmark_columns,
                )
                for strategy in strategy_columns
            },
        }
        for window in windows
    }
    center_vs_equal_weight = {
        window: {
            benchmark: rolling[str(window)]["comparisons"][
                "v1b_center_0_6_hold_40_buffer_0_05_20bps"
            ][benchmark]["negative_window_reduction"]
            for benchmark in [
                "fixed_40_equal_weight",
                "fixed_50_equal_weight",
                "fixed_60_equal_weight",
            ]
        }
        for window in windows
    }
    center_has_stable_negative_window_reduction = all(
        value > 0 for row in center_vs_equal_weight.values() for value in row.values()
    )
    output = {
        "status": "research_only",
        "not_trading_permission": True,
        "experiment": "v1b_path_smoothing_utility",
        "method_note": (
            "Test whether v1b's remaining path-smoothing claim is stable across 252/504/756 "
            "session rolling windows against simple fixed exposure baselines. No parameter search."
        ),
        "data_root": str(DATA_ROOT.relative_to(REPO_ROOT)),
        "strategy_cases": run_meta,
        "full_period": full_period,
        "rolling_windows": rolling,
        "center_vs_equal_weight_negative_window_reduction": center_vs_equal_weight,
        "center_has_stable_negative_window_reduction_vs_equal_weight": (
            center_has_stable_negative_window_reduction
        ),
        "decision": (
            "RETIRE_V1B_MAINLINE"
            if not center_has_stable_negative_window_reduction
            else "HOLD_FOR_INVESTOR_UTILITY_DEFINITION"
        ),
    }
    ARTIFACT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            output["center_vs_equal_weight_negative_window_reduction"],
            ensure_ascii=False,
            indent=2,
        )
    )
    print(output["decision"])


if __name__ == "__main__":
    main()
