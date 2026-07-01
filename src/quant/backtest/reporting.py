from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from quant.core.config import BenchmarkConfig, StrategyConfig


RESEARCH_ONLY_DISCLAIMER = (
    "Research-only disclaimer: this report is backtest evidence only. "
    "It is not trading permission, investment advice, or approval for any execution stage."
)


def write_research_report_artifacts(
    result: Any,
    output_dir: Path,
    config: StrategyConfig,
    *,
    data_root: Path | None = None,
) -> dict[str, Any]:
    data_root = Path(data_root) if data_root is not None else None
    manifest = _load_manifest(data_root)
    manifest_copied = _copy_dataset_manifest(data_root, output_dir)
    report = build_research_report(
        result,
        config,
        data_root=data_root,
        manifest=manifest,
        manifest_copied=manifest_copied,
    )
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(render_markdown_report(report), encoding="utf-8")
    return report


def build_research_report(
    result: Any,
    config: StrategyConfig,
    *,
    data_root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    manifest_copied: bool = False,
) -> dict[str, Any]:
    equity = list(getattr(result, "equity", []))
    trades = list(getattr(result, "trades", []))
    events = list(getattr(result, "events", []))
    cost_inputs = dict(getattr(result, "cost_report_inputs", {}) or {})
    data_period = _data_period(equity, manifest)
    total_values = [_number(row.get("total_value")) for row in equity]

    report = {
        "not_trading_permission": True,
        "strategy_id": config.id,
        "strategy_metrics": _strategy_metrics(total_values),
        "turnover": _turnover(trades),
        "rebalance_count": _rebalance_count(events),
        "time_in_cash": _time_in_cash(equity),
        "time_by_symbol": _time_by_symbol(trades),
        "total_fee": _number(
            cost_inputs.get(
                "total_fee",
                sum(_number(getattr(trade, "commission", 0.0)) for trade in trades),
            )
        ),
        "estimated_slippage_cost": _number(cost_inputs.get("estimated_slippage_cost", 0.0)),
        "cost_preset_name": cost_inputs.get("preset", config.costs.preset),
        "costs": cost_inputs,
        "benchmarks": _benchmark_reports(config, data_root, manifest, data_period),
        "data_period": data_period,
        "timezone": _timezone(manifest),
        "risk_stop_summary": _risk_stop_summary(events),
        "dataset_manifest_copied": manifest_copied,
    }
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    metrics = report["strategy_metrics"]
    lines = [
        "# Research Report",
        "",
        RESEARCH_ONLY_DISCLAIMER,
        "",
        "## Summary",
        "",
        f"- Strategy ID: {report['strategy_id']}",
        f"- Initial value: {metrics.get('initial_value')}",
        f"- Final value: {metrics.get('final_value')}",
        f"- Return pct: {metrics.get('return_pct')}",
        f"- Max drawdown pct: {metrics.get('max_drawdown_pct')}",
        f"- Turnover: {report['turnover']}",
        f"- Rebalance count: {report['rebalance_count']}",
        f"- Total fee: {report['total_fee']}",
        f"- Estimated slippage cost: {report['estimated_slippage_cost']}",
        "",
        "## Benchmarks",
        "",
    ]
    benchmarks = report.get("benchmarks", {})
    if not benchmarks:
        lines.append("- No benchmarks configured.")
    for benchmark_id, benchmark in benchmarks.items():
        metrics = benchmark.get("metrics", {})
        lines.append(
            "- "
            f"{benchmark_id}: type={benchmark.get('type')}, "
            f"return_pct={metrics.get('return_pct')}, "
            f"max_drawdown_pct={metrics.get('max_drawdown_pct')}"
        )
    lines.append("")
    return "\n".join(lines)


def _copy_dataset_manifest(data_root: Path | None, output_dir: Path) -> bool:
    if data_root is None:
        return False
    source = data_root / "dataset_manifest.yaml"
    if not source.exists():
        return False
    shutil.copyfile(source, output_dir / "dataset_manifest.yaml")
    return True


def _load_manifest(data_root: Path | None) -> dict[str, Any] | None:
    if data_root is None:
        return None
    path = data_root / "dataset_manifest.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _data_period(
    equity: list[dict[str, Any]],
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if equity:
        return {
            "start": _text(equity[0].get("dt")),
            "end": _text(equity[-1].get("dt")),
            "equity_rows": len(equity),
        }
    coverage = manifest.get("coverage") if manifest is not None else None
    if isinstance(coverage, dict):
        return {
            "start": _text(coverage.get("start")),
            "end": _text(coverage.get("end")),
            "equity_rows": 0,
        }
    return {"start": None, "end": None, "equity_rows": 0}


def _strategy_metrics(total_values: list[float]) -> dict[str, float | None]:
    if not total_values:
        return {
            "initial_value": None,
            "final_value": None,
            "return_pct": None,
            "max_drawdown_pct": None,
        }
    initial_value = total_values[0]
    final_value = total_values[-1]
    return {
        "initial_value": _round4(initial_value),
        "final_value": _round4(final_value),
        "return_pct": _round4((final_value / initial_value - 1.0) * 100) if initial_value else 0.0,
        "max_drawdown_pct": _max_drawdown_pct(total_values),
    }


def _turnover(trades: list[Any]) -> float:
    notional = (
        _number(getattr(trade, "qty", 0.0)) * _number(getattr(trade, "price", 0.0))
        for trade in trades
    )
    return _round4(sum(notional))


def _rebalance_count(events: list[Any]) -> int:
    return sum(1 for event in events if getattr(event, "event_type", None) == "rebalance_decision")


def _time_in_cash(equity: list[dict[str, Any]]) -> float:
    if not equity:
        return 0.0
    cash_rows = 0
    for row in equity:
        total_value = _number(row.get("total_value"))
        cash = _number(row.get("cash"))
        if total_value == 0:
            continue
        if abs(cash - total_value) <= max(abs(total_value) * 1e-9, 1e-9):
            cash_rows += 1
    return cash_rows / len(equity)


def _time_by_symbol(trades: list[Any]) -> dict[str, float]:
    counts = Counter(
        str(getattr(trade, "symbol", ""))
        for trade in trades
        if getattr(trade, "symbol", "")
    )
    total = sum(counts.values())
    if total == 0:
        return {}
    return {symbol: count / total for symbol, count in sorted(counts.items())}


def _risk_stop_summary(events: list[Any]) -> dict[str, Any]:
    stop_events = [
        event for event in events if getattr(event, "event_type", None) == "risk_portfolio_stop"
    ]
    latest = stop_events[-1] if stop_events else None
    payload = getattr(latest, "payload", {}) if latest is not None else {}
    return {
        "triggered_events": len(stop_events),
        "latest_state": payload.get("cycle_state"),
        "latest_reason": payload.get("reason"),
    }


def _benchmark_reports(
    config: StrategyConfig,
    data_root: Path | None,
    manifest: dict[str, Any] | None,
    data_period: dict[str, Any],
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for benchmark in config.benchmarks:
        if benchmark.type == "cash":
            reports[benchmark.id] = _cash_benchmark(benchmark, data_period)
            continue
        if data_root is None:
            reports[benchmark.id] = _unavailable_benchmark(benchmark, "data_root not provided")
            continue
        try:
            if benchmark.type == "single_asset_buy_hold":
                reports[benchmark.id] = _single_asset_benchmark(
                    benchmark,
                    data_root,
                    config.primary_frequency,
                    manifest,
                )
            elif benchmark.type == "equal_weight_buy_hold":
                reports[benchmark.id] = _equal_weight_benchmark(
                    benchmark,
                    data_root,
                    config,
                    manifest,
                )
            else:
                reports[benchmark.id] = _unavailable_benchmark(
                    benchmark,
                    f"unsupported benchmark type {benchmark.type!r}",
                )
        except Exception as exc:
            reports[benchmark.id] = _unavailable_benchmark(benchmark, str(exc))
    return reports


def _cash_benchmark(
    benchmark: BenchmarkConfig,
    data_period: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": benchmark.type,
        "status": "PASS",
        "period": {
            "start": data_period.get("start"),
            "end": data_period.get("end"),
            "rows": data_period.get("equity_rows"),
        },
        "metrics": {
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
        },
    }


def _single_asset_benchmark(
    benchmark: BenchmarkConfig,
    data_root: Path,
    frequency: str,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if not benchmark.symbol:
        raise ValueError("single_asset_buy_hold benchmark requires symbol")
    rows = _load_symbol_rows(data_root, frequency, manifest, [benchmark.symbol])[benchmark.symbol]
    metrics = _buy_hold_metrics(rows)
    return {
        "type": benchmark.type,
        "status": "PASS",
        "symbol": benchmark.symbol,
        "period": {
            "start": rows[0]["dt"],
            "end": rows[-1]["dt"],
            "rows": len(rows),
        },
        "metrics": metrics,
    }


def _equal_weight_benchmark(
    benchmark: BenchmarkConfig,
    data_root: Path,
    config: StrategyConfig,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    symbols = list(benchmark.symbols or config.universe)
    if not symbols:
        raise ValueError("equal_weight_buy_hold benchmark requires symbols")
    by_symbol = _load_symbol_rows(data_root, config.primary_frequency, manifest, symbols)
    date_sets = [set(row["dt"] for row in rows) for rows in by_symbol.values()]
    common_dates = sorted(set.intersection(*date_sets))
    if not common_dates:
        raise ValueError("no common benchmark dates")

    rows_by_symbol_date = {
        symbol: {row["dt"]: row for row in rows}
        for symbol, rows in by_symbol.items()
    }
    first_close = {
        symbol: _number(rows_by_symbol_date[symbol][common_dates[0]]["close"])
        for symbol in symbols
    }
    equity = []
    for date in common_dates:
        ratios = []
        for symbol in symbols:
            base = first_close[symbol]
            if base == 0:
                raise ValueError(f"first close is zero for {symbol}")
            ratios.append(_number(rows_by_symbol_date[symbol][date]["close"]) / base)
        equity.append(100_000.0 * sum(ratios) / len(ratios))

    return {
        "type": benchmark.type,
        "status": "PASS",
        "symbols": symbols,
        "period": {
            "start": common_dates[0],
            "end": common_dates[-1],
            "rows": len(common_dates),
        },
        "metrics": {
            "return_pct": _round4((equity[-1] / equity[0] - 1.0) * 100),
            "max_drawdown_pct": _max_drawdown_pct(equity),
        },
    }


def _unavailable_benchmark(benchmark: BenchmarkConfig, reason: str) -> dict[str, Any]:
    return {
        "type": benchmark.type,
        "status": "UNAVAILABLE",
        "reason": reason,
        "metrics": {},
    }


def _load_symbol_rows(
    data_root: Path,
    frequency: str,
    manifest: dict[str, Any] | None,
    symbols: list[str],
) -> dict[str, list[dict[str, str]]]:
    rows_by_symbol: dict[str, list[dict[str, str]]] = {symbol: [] for symbol in symbols}
    with _bar_file(data_root, frequency, manifest).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            symbol = row.get("symbol", "")
            if symbol not in rows_by_symbol:
                continue
            if row.get("data_status", "ok") != "ok":
                continue
            rows_by_symbol[symbol].append(row)
    for symbol, rows in rows_by_symbol.items():
        if not rows:
            raise ValueError(f"no bars for {symbol}")
        rows.sort(key=lambda row: row["dt"])
    return rows_by_symbol


def _bar_file(data_root: Path, frequency: str, manifest: dict[str, Any] | None) -> Path:
    if manifest is not None:
        frequencies = manifest.get("frequencies", [])
        if isinstance(frequencies, list):
            for item in frequencies:
                if isinstance(item, dict) and item.get("freq") == frequency and item.get("file"):
                    return data_root / str(item["file"])
    return data_root / f"bars_{frequency}.csv"


def _buy_hold_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    equity = _normalized_equity(rows)
    return {
        "return_pct": _round4((equity[-1] / equity[0] - 1.0) * 100),
        "max_drawdown_pct": _max_drawdown_pct(equity),
    }


def _normalized_equity(rows: list[dict[str, str]]) -> list[float]:
    first_close = _number(rows[0]["close"])
    if first_close == 0:
        raise ValueError("first close is zero")
    return [100_000.0 * _number(row["close"]) / first_close for row in rows]


def _max_drawdown_pct(values: list[float]) -> float:
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = (value - peak) / peak if peak else 0.0
        max_drawdown = min(max_drawdown, drawdown)
    return _round4(max_drawdown * 100)


def _timezone(manifest: dict[str, Any] | None) -> str | None:
    if manifest is None:
        return None
    timezone = manifest.get("timezone")
    return str(timezone) if timezone is not None else None


def _round4(value: float) -> float:
    return round(float(value), 4)


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
