from pathlib import Path


def test_m3b_observation_checklist_captures_paper_gate_requirements() -> None:
    text = Path("docs/runbooks/paper_observation_checklist.md").read_text(encoding="utf-8")
    required = [
        "10 trading days",
        "daily reconciliation zero difference",
        "disconnect drill",
        "CRIT alert delivery",
        "no unresolved manual intervention",
        "M4 is blocked until this checklist is complete",
    ]
    for phrase in required:
        assert phrase in text
