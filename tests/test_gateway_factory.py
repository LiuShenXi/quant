from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from quant.core.contract import Account, Position
from quant.live.config import load_paper_config
from quant.live.gateway.factory import build_sim_gateway
from quant.live.store import OmsStore


def test_build_sim_gateway_uses_initial_cash_without_snapshot(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
            "initial_cash": 123_456,
        }
    )

    gateway = build_sim_gateway(paper_config, store)

    assert gateway.query_account().cash == 123_456


def test_build_sim_gateway_restores_account_snapshot(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    account = Account(
        account_id="paper",
        currency="CNY",
        cash=88_000,
        frozen=0,
        market_value=12_000,
        total_value=100_000,
    )
    positions = {
        "510300.SH": Position(
            account_id="paper",
            symbol="510300.SH",
            qty=3000,
            sellable=2000,
            avg_price=4.0,
            market_value=12_000,
        )
    }
    store.save_account_snapshot(
        account,
        positions,
        datetime(2026, 6, 25, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )

    gateway = build_sim_gateway(paper_config, store)

    assert gateway.query_account().cash == 88_000
    assert gateway.query_positions()["510300.SH"].sellable == 2000
