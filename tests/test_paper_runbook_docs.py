from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_readme_names_m3a_m3b_and_blocks_m4_until_m3b_gate() -> None:
    readme = normalized("README.md")

    required_phrases = [
        "M3a is deterministic local Paper replay",
        "M3b is the real-money-pre-gate observation process",
        "10 trading days",
        "daily reconciliation zero difference",
        "one disconnect drill",
        "verified CRIT alert delivery",
        "no unresolved manual intervention",
        "M4 remains blocked until the M3b gate is complete",
    ]

    for phrase in required_phrases:
        assert phrase in readme


def test_paper_runbook_acceptance_log_lists_all_m3b_gate_conditions() -> None:
    runbook = normalized("docs/runbooks/paper_daily_runbook.md")

    required_phrases = [
        "10 trading days",
        "daily reconciliation zero difference",
        "one disconnect drill",
        "verified CRIT alert delivery",
        "no unresolved manual intervention",
    ]

    for phrase in required_phrases:
        assert phrase in runbook
