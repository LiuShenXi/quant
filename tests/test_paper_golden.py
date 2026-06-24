import filecmp
import sqlite3
from pathlib import Path

from quant.core.config import load_strategy_config
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine


def dump_table(db_path: Path, table: str, output: Path) -> None:
    with sqlite3.connect(db_path) as conn, output.open("w", encoding="utf-8") as file:
        cursor = conn.execute(f"select * from {table} order by 1")
        file.write(",".join([column[0] for column in cursor.description]) + "\n")
        for row in cursor.fetchall():
            file.write(",".join("" if value is None else str(value) for value in row) + "\n")


def test_paper_replay_matches_golden(tmp_path) -> None:
    config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )
    PaperEngine(
        load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml")),
        config,
    ).run_replay(max_bars=20)

    dump_table(tmp_path / "meta.db", "orders", tmp_path / "orders.csv")
    dump_table(tmp_path / "meta.db", "trades", tmp_path / "trades.csv")
    assert filecmp.cmp(
        tmp_path / "orders.csv",
        Path("tests/golden_paper/orders.csv"),
        shallow=False,
    )
    assert filecmp.cmp(
        tmp_path / "trades.csv",
        Path("tests/golden_paper/trades.csv"),
        shallow=False,
    )
    assert filecmp.cmp(
        tmp_path / "events.jsonl",
        Path("tests/golden_paper/events.jsonl"),
        shallow=False,
    )
