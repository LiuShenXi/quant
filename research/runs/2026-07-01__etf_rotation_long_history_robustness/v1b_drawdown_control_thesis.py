from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import pandas as pd
from v1b_regime_failure_review import (
    ARTIFACT_PATH as REGIME_ARTIFACT_PATH,
)
from v1b_regime_failure_review import (
    CaseSpec,
    load_benchmark_equity,
    max_drawdown,
    period_metrics,
    return_pct,
    run_strategy,
)

RUN_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = RUN_DIR / "artifacts" / "v1b_drawdown_control_thesis.json"


def rolling_window_stats(
    frame: pd.DataFrame,
    strategy_column: str,
    benchmark_column: str,
    window: int = 504,
) -> dict[str, float | int]:
    return_gaps: list[float] = []
    drawdown_improvements: list[float] = []
    strategy_negative = 0
    benchmark_negative = 0
    strategy_lower_drawdown = 0
    strategy_higher_return = 0
    materially_better_drawdown = 0
    for start in range(0, len(frame) - window + 1):
        group = frame.iloc[start : start + window]
        strategy_return = return_pct(group[strategy_column])
        benchmark_return = return_pct(group[benchmark_column])
        strategy_dd = max_drawdown(group[strategy_column])
        benchmark_dd = max_drawdown(group[benchmark_column])
        return_gaps.append(round(strategy_return - benchmark_return, 4))
        drawdown_improvement = round(strategy_dd - benchmark_dd, 4)
        drawdown_improvements.append(drawdown_improvement)
        strategy_negative += int(strategy_return < 0)
        benchmark_negative += int(benchmark_return < 0)
        strategy_lower_drawdown += int(drawdown_improvement > 0)
        strategy_higher_return += int(strategy_return > benchmark_return)
        materially_better_drawdown += int(drawdown_improvement >= 3.0)
    return {
        "window_sessions": window,
        "windows": len(return_gaps),
        "strategy_negative_windows": strategy_negative,
        "benchmark_negative_windows": benchmark_negative,
        "negative_window_reduction": benchmark_negative - strategy_negative,
        "strategy_higher_return_windows": strategy_higher_return,
        "strategy_lower_drawdown_windows": strategy_lower_drawdown,
        "materially_better_drawdown_windows_ge_3pct": materially_better_drawdown,
        "median_return_gap_pct": round(median(return_gaps), 4),
        "min_return_gap_pct": round(min(return_gaps), 4),
        "max_return_gap_pct": round(max(return_gaps), 4),
        "median_drawdown_improvement_pct": round(median(drawdown_improvements), 4),
        "min_drawdown_improvement_pct": round(min(drawdown_improvements), 4),
        "max_drawdown_improvement_pct": round(max(drawdown_improvements), 4),
    }


def full_period_comparison(
    full_period: dict[str, dict[str, float]],
    strategy_column: str,
    benchmark_column: str,
) -> dict[str, float | None]:
    strategy = full_period[strategy_column]
    benchmark = full_period[benchmark_column]
    return_gap = round(strategy["return_pct"] - benchmark["return_pct"], 4)
    drawdown_improvement = round(
        strategy["max_drawdown_pct"] - benchmark["max_drawdown_pct"],
        4,
    )
    if return_gap < 0 and drawdown_improvement > 0:
        return_loss_per_drawdown_point = round(abs(return_gap) / drawdown_improvement, 4)
    else:
        return_loss_per_drawdown_point = None
    return {
        "strategy_return_pct": strategy["return_pct"],
        "benchmark_return_pct": benchmark["return_pct"],
        "return_gap_pct": return_gap,
        "strategy_max_drawdown_pct": strategy["max_drawdown_pct"],
        "benchmark_max_drawdown_pct": benchmark["max_drawdown_pct"],
        "drawdown_improvement_pct": drawdown_improvement,
        "return_loss_per_drawdown_improvement_point": return_loss_per_drawdown_point,
    }


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
    frame = load_benchmark_equity()
    for case in cases:
        strategy_frame, _meta = run_strategy(case, slippage_bps=20.0)
        frame = frame.merge(strategy_frame, on="dt", how="inner")
    return frame


def main() -> None:
    benchmark_columns = [
        "fixed_60_equal_weight",
        "fixed_60_510300_SH",
        "fixed_60_510500_SH",
    ]
    strategy_columns = [
        "v1b_center_0_6_hold_40_buffer_0_05_20bps",
        "v1b_best20_0_7_hold_30_buffer_0_07_20bps",
    ]
    frame = build_equity_frame()
    columns = [*strategy_columns, *benchmark_columns]
    full_period = {column: period_metrics(frame, column) for column in columns}
    comparisons = {
        strategy: {
            benchmark: {
                "full_period": full_period_comparison(full_period, strategy, benchmark),
                "rolling_504_sessions": rolling_window_stats(frame, strategy, benchmark),
            }
            for benchmark in benchmark_columns
        }
        for strategy in strategy_columns
    }
    equal_weight_checks = {
        strategy: comparisons[strategy]["fixed_60_equal_weight"] for strategy in strategy_columns
    }
    output = {
        "status": "research_only",
        "not_trading_permission": True,
        "experiment": "v1b_drawdown_control_thesis_review",
        "method_note": (
            "Evaluate whether v1b's lower drawdown and fewer negative rolling windows "
            "justify a research-only drawdown-control thesis. No parameter search."
        ),
        "source_regime_artifact": str(REGIME_ARTIFACT_PATH.relative_to(RUN_DIR)),
        "full_period": full_period,
        "comparisons": comparisons,
        "equal_weight_summary": equal_weight_checks,
        "decision": "CONTINUE_RESEARCH_ONLY_DRAWDOWN_CONTROL_THESIS",
        "cio_interpretation": {
            "paper_gate": "FAIL",
            "live_gate": "FAIL",
            "summary": (
                "v1b fails as an absolute-return enhancement strategy, but the drawdown-control "
                "thesis remains researchable because it reduces max drawdown and negative "
                "504-session windows versus fixed 60% equal-weight exposure. The cost is a "
                "large full-period return sacrifice, so this is not paper eligible."
            ),
        },
    }
    ARTIFACT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["equal_weight_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
