import csv
import filecmp
import sqlite3
from pathlib import Path

from quant.core.config import load_strategy_config
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine


def dump_table(db_path: Path, table: str, output: Path) -> None:
    with sqlite3.connect(db_path) as conn, output.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        cursor = conn.execute(f"select * from {table} order by 1")
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow([column[0] for column in cursor.description])
        for row in cursor.fetchall():
            writer.writerow("" if value is None else value for value in row)


def assert_has_data_rows(path: Path) -> None:
    rows = path.read_text(encoding="utf-8").splitlines()
    assert len(rows) > 1, f"{path} must include at least one data row"


def assert_text_rows_match(actual: Path, expected: Path) -> None:
    assert actual.read_text(encoding="utf-8").splitlines() == expected.read_text(
        encoding="utf-8"
    ).splitlines()


def test_paper_replay_matches_golden(tmp_path) -> None:
    strategy_config = load_strategy_config(
        Path("config/strategies/dual_ma_510300_paper.yaml")
    ).model_copy(
        update={
            "class_path": "tests.paper_golden_strategy:GoldenPaperStrategy",
            "id": "paper_golden_strategy",
            "params": {
                "symbol": "510300.SH",
                "target_qty": 1000,
            },
        }
    )
    config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )
    PaperEngine(strategy_config, config).run_replay(max_bars=20)

    dump_table(tmp_path / "meta.db", "orders", tmp_path / "orders.csv")
    dump_table(tmp_path / "meta.db", "trades", tmp_path / "trades.csv")
    assert_has_data_rows(tmp_path / "orders.csv")
    assert_has_data_rows(tmp_path / "trades.csv")
    assert_has_data_rows(Path("tests/golden_paper/orders.csv"))
    assert_has_data_rows(Path("tests/golden_paper/trades.csv"))
    assert_text_rows_match(tmp_path / "orders.csv", Path("tests/golden_paper/orders.csv"))
    assert_text_rows_match(tmp_path / "trades.csv", Path("tests/golden_paper/trades.csv"))
    assert filecmp.cmp(
        tmp_path / "events.jsonl",
        Path("tests/golden_paper/events.jsonl"),
        shallow=False,
    )
