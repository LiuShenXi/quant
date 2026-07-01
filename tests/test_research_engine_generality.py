from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from types import ModuleType

import yaml

from quant.backtest.engine import BacktestEngine
from quant.backtest.results import write_result
from quant.core.config import load_strategy_config
from quant.core.contract import OrderSide, StrategyBase
from quant.data.service import DataService


TOY_FIXTURE = Path("tests/fixtures/toy_multifreq_24x7")
CRYPTO_FIXTURE = Path("tests/fixtures/crypto_trend_breadth_acceptance")
PLATFORM_SOURCE_ROOTS = [
    Path("src/quant/backtest"),
    Path("src/quant/core"),
    Path("src/quant/data"),
    Path("src/quant/risk"),
]
FORBIDDEN_PLATFORM_PATTERNS = {
    "crypto_trend_breadth_top2_v1": re.compile(r"crypto_trend_breadth_top2_v1"),
    "crypto_asset_symbol": re.compile(r"\b(?:BTC|ETH|SOL)\b"),
    "strategy_weight_shorthand": re.compile(r"60\s*/\s*40"),
    "five_day_cooldown": re.compile(
        r"5\s*-\s*day\s+cooldown|5\s+day\s+cooldown|cooldown_days\s*[:=]\s*5|timedelta\(\s*days\s*=\s*5\s*\)",
        re.IGNORECASE,
    ),
    "thirty_five_pct_red_line": re.compile(
        r"35\s*%\s*(?:red\s+line|review|drawdown)|(?:max_)?drawdown\w*\s*[:=]\s*0\.35|red_line\w*\s*[:=]\s*0\.35",
        re.IGNORECASE,
    ),
}


def test_toy_multifreq_24x7_fixture_runs_generic_research_engine(
    monkeypatch,
    tmp_path: Path,
) -> None:
    observations: list[dict[str, object]] = []
    config = load_strategy_config(TOY_FIXTURE / "strategy.yaml")
    config = config.model_copy(
        update={
            "params": {
                **config.params,
                "observations": observations,
            }
        }
    )
    assert getattr(config.risk, "portfolio_stop", None) is not None

    strategy_module = ModuleType("tests.toy_multifreq_acceptance_strategy")

    class ToyMultifreqAcceptanceStrategy(StrategyBase):
        def on_init(self, ctx) -> None:
            self.signal_symbol = ctx.params["signal_symbol"]
            self.target_weights = dict(ctx.params["target_weights"])
            self.observations = ctx.params["observations"]

        def on_bar(self, ctx, bar) -> None:
            if bar.symbol != self.signal_symbol:
                return
            history = ctx.history(self.signal_symbol, n=5, freq="1d", adjust="raw")
            history_max = None if history.empty else history["dt"].max().to_pydatetime()
            visible_daily = ctx.get_visible_bar_time("1d")
            daily_bar = ctx.get_bar(self.signal_symbol, freq="1d")
            self.observations.append(
                {
                    "now": ctx.now,
                    "history_max": history_max,
                    "visible_daily": visible_daily,
                    "daily_bar_dt": None if daily_bar is None else daily_bar.dt,
                }
            )
            if history.empty or len(history) < 2:
                return
            if float(history.iloc[-1]["close"]) <= float(history.iloc[-2]["close"]):
                return
            for symbol, weight in self.target_weights.items():
                ctx.set_target_weight(symbol, float(weight))

    strategy_module.ToyMultifreqAcceptanceStrategy = ToyMultifreqAcceptanceStrategy
    monkeypatch.setattr(
        "quant.backtest.engine.import_module",
        lambda name: (
            strategy_module
            if name == "tests.toy_multifreq_acceptance_strategy"
            else None
        ),
    )

    result = BacktestEngine(
        config=config,
        data=DataService(TOY_FIXTURE),
        initial_cash=1_000,
    ).run()
    output_dir = tmp_path / "toy_result"
    write_result(result, output_dir=output_dir, config=config, data_root=TOY_FIXTURE)

    assert config.universe == ["AAA", "BBB", "CCC"]
    assert config.calendar == "continuous_24x7"
    assert config.primary_frequency == "4h"
    assert set(config.history_frequencies) == {"4h", "1d"}
    assert observations
    assert all(
        observation["history_max"] is None
        or observation["history_max"] <= observation["now"]
        for observation in observations
    )
    assert all(
        observation["daily_bar_dt"] == observation["visible_daily"]
        for observation in observations
    )
    assert any(
        observation["now"] < datetime.fromisoformat("2026-01-02T00:00:00+00:00")
        and observation["visible_daily"]
        == datetime.fromisoformat("2026-01-01T00:00:00+00:00")
        for observation in observations
    )

    event_types = [event.event_type for event in result.events]
    for event_type in [
        "engine_state",
        "target_intent",
        "rebalance_decision",
        "risk_check",
        "order_submitted",
        "fill",
        "cash_transition",
        "risk_portfolio_stop",
        "risk_cooldown_start",
        "target_intent_rejected",
    ]:
        assert event_type in event_types

    first_target = next(event for event in result.events if event.event_type == "target_intent")
    first_fill = next(event for event in result.events if event.event_type == "fill")
    assert first_target.payload["target_weight"] in config.params["target_weights"].values()
    assert first_fill.timestamp > datetime.fromisoformat(
        first_target.payload["source_bar_timestamp"]
    )
    assert any(trade.side == OrderSide.BUY for trade in result.trades)
    assert any(trade.side == OrderSide.SELL for trade in result.trades)
    assert any(
        trade.qty != int(trade.qty)
        for trade in result.trades
        if trade.side == OrderSide.BUY
    )
    assert result.cost_report_inputs["model"] == "bps"
    assert result.cost_report_inputs["fee_bps"] == 10.0
    assert result.cost_report_inputs["total_fee"] > 0
    assert result.cost_report_inputs["estimated_slippage_cost"] > 0
    assert any(
        event.event_type == "target_intent_rejected"
        and event.risk_rule_id == "portfolio_stop_cooldown"
        for event in result.events
    )
    assert [event.seq for event in result.events] == list(range(1, len(result.events) + 1))

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "report.md").read_text(encoding="utf-8")
    assert report["not_trading_permission"] is True
    assert "research-only" in markdown.lower()
    assert "not trading permission" in markdown.lower()


def test_crypto_trend_breadth_acceptance_fixture_stays_configuration_level() -> None:
    config = load_strategy_config(CRYPTO_FIXTURE / "strategy.yaml")
    manifest = yaml.safe_load((CRYPTO_FIXTURE / "dataset_manifest.yaml").read_text(encoding="utf-8"))

    assert config.id == "crypto_trend_breadth_top2_v1"
    assert config.calendar == "continuous_24x7"
    assert config.primary_frequency == "4h"
    assert set(config.history_frequencies) == {"4h", "1d"}
    assert config.account.currency == "USDT"
    assert config.account.allow_fractional is True
    assert config.costs.model == "bps"
    assert getattr(config.risk, "portfolio_stop", None) is not None
    assert {item["symbol"] for item in manifest["symbols"]} == {"BTC", "ETH", "SOL"}
    assert {item["freq"] for item in manifest["frequencies"]} == {"4h", "1d"}
    assert config.params["rank_symbols"] == ["BTC", "ETH", "SOL"]
    assert _platform_source_scan_violations(PLATFORM_SOURCE_ROOTS) == []


def test_platform_source_has_no_strategy_specific_research_constants() -> None:
    assert _platform_source_scan_violations(PLATFORM_SOURCE_ROOTS) == []


def test_platform_source_scan_rejects_strategy_specific_literals(tmp_path: Path) -> None:
    source_root = tmp_path / "src" / "quant" / "backtest"
    source_root.mkdir(parents=True)
    (source_root / "engine.py").write_text(
        "\n".join(
            [
                "STRATEGY = 'crypto_trend_breadth_top2_v1'",
                "UNIVERSE = ['BTC', 'ETH', 'SOL']",
                "WEIGHTS = '60/40'",
                "COOLDOWN = '5-day cooldown'",
                "RED_LINE = '35% red line'",
            ]
        ),
        encoding="utf-8",
    )

    violations = _platform_source_scan_violations([source_root])

    assert {violation.reason for violation in violations} == set(FORBIDDEN_PLATFORM_PATTERNS)


class PlatformSourceViolation:
    def __init__(self, path: Path, reason: str, snippet: str) -> None:
        self.path = path
        self.reason = reason
        self.snippet = snippet

    def __repr__(self) -> str:
        return f"{self.path}: {self.reason}: {self.snippet!r}"


def _platform_source_scan_violations(roots: list[Path]) -> list[PlatformSourceViolation]:
    violations: list[PlatformSourceViolation] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for reason, pattern in FORBIDDEN_PLATFORM_PATTERNS.items():
                match = pattern.search(text)
                if match is not None:
                    violations.append(
                        PlatformSourceViolation(
                            path=path,
                            reason=reason,
                            snippet=match.group(0),
                        )
                    )
    return violations
