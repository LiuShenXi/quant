from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
CASES_PATH = ROOT / "tests" / "fixtures" / "quant_skill_pressure_cases.yaml"
BACKTEST_SCRIPT = (
    SKILLS_ROOT / "backtest-validator" / "scripts" / "inspect_backtest_artifacts.py"
)
REAL_BACKTEST_DIR = (
    ROOT
    / "research"
    / "imported"
    / "usage_records"
    / "2026-06-26__quant_usage_record"
    / "backtest"
    / "dual_ma_510300_20_60"
)


EXPECTED_SKILLS = {
    "strategy-thesis-tracker",
    "data-audit-reviewer",
    "backtest-validator",
    "risk-governor",
    "paper-live-gatekeeper",
}


FRONTMATTER_RE = re.compile(
    r"^---\s*\nname:\s*(?P<name>[-a-z0-9]+)\s*\n"
    r"description:\s*(?P<description>.+?)\n---\s*\n",
    re.DOTALL,
)


@pytest.fixture(scope="module")
def cases() -> dict:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))


def skill_text(name: str) -> str:
    return (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")


def skill_metadata(name: str) -> tuple[str, str]:
    match = FRONTMATTER_RE.match(skill_text(name))
    assert match, f"{name} has invalid frontmatter"
    return match.group("name"), match.group("description")


def test_expected_skill_inventory_exists() -> None:
    actual = {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()}
    assert EXPECTED_SKILLS <= actual


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_skill_frontmatter_is_discovery_safe(skill_name: str) -> None:
    name, description = skill_metadata(skill_name)
    assert name == skill_name
    assert description.startswith("Use when ")
    assert len(description) <= 500
    assert re.fullmatch(r"[-a-z0-9]+", name)


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_declared_references_and_scripts_exist(skill_name: str) -> None:
    text = skill_text(skill_name)
    for relative in re.findall(r"`((?:references|scripts)/[^`]+)`", text):
        assert (SKILLS_ROOT / skill_name / relative).exists(), f"{skill_name}: {relative}"


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_descriptions_cover_trigger_terms(skill_name: str, cases: dict) -> None:
    _, description = skill_metadata(skill_name)
    lowered = description.lower()
    for term in cases["skills"][skill_name]["description_terms"]:
        assert term.lower() in lowered, f"{skill_name} description missing {term!r}"


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_skill_body_contains_required_boundaries(skill_name: str, cases: dict) -> None:
    combined_text = skill_text(skill_name)
    references_dir = SKILLS_ROOT / skill_name / "references"
    if references_dir.exists():
        for ref in references_dir.glob("*.md"):
            combined_text += "\n" + ref.read_text(encoding="utf-8")

    for term in cases["skills"][skill_name]["boundary_terms"]:
        assert term in combined_text, f"{skill_name} missing boundary {term!r}"


def score_prompt(prompt: str, keywords: list[str]) -> int:
    lowered = prompt.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_positive_prompt_matrix_selects_expected_skill(skill_name: str, cases: dict) -> None:
    all_skill_cases = cases["skills"]
    for prompt in all_skill_cases[skill_name]["should_trigger"]:
        scores = {
            candidate: score_prompt(prompt, data["selection_keywords"])
            for candidate, data in all_skill_cases.items()
        }
        expected_score = scores[skill_name]
        competing_scores = {name: score for name, score in scores.items() if name != skill_name}
        assert expected_score > 0, f"{skill_name} has no trigger score for {prompt!r}"
        assert expected_score >= max(competing_scores.values()), (prompt, scores)


@pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
def test_negative_prompt_matrix_does_not_select_skill(skill_name: str, cases: dict) -> None:
    all_skill_cases = cases["skills"]
    for prompt in all_skill_cases[skill_name]["should_not_trigger"]:
        score = score_prompt(prompt, all_skill_cases[skill_name]["selection_keywords"])
        assert score == 0, f"{skill_name} over-matches {prompt!r} with score {score}"


@pytest.mark.parametrize("case", yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["unsafe_prompts"])
def test_unsafe_prompt_pressure_cases_have_explicit_guardrails(case: dict, cases: dict) -> None:
    expected_skill = case["expected_skill"]
    scores = {
        candidate: score_prompt(case["prompt"], data["selection_keywords"])
        for candidate, data in cases["skills"].items()
    }
    assert scores[expected_skill] >= max(scores.values())

    combined_text = skill_text(expected_skill)
    references_dir = SKILLS_ROOT / expected_skill / "references"
    if references_dir.exists():
        combined_text += "\n" + "\n".join(
            path.read_text(encoding="utf-8") for path in references_dir.glob("*.md")
        )
    assert case["required_boundary"] in combined_text


def test_backtest_inspection_script_is_importable() -> None:
    spec = importlib.util.spec_from_file_location("inspect_backtest_artifacts", BACKTEST_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "inspect_artifacts")


def test_backtest_inspection_script_passes_real_artifact_directory() -> None:
    completed = subprocess.run(
        [sys.executable, str(BACKTEST_SCRIPT), str(REAL_BACKTEST_DIR)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["blocking_issues"] == []
    assert payload["files"]["equity"]["rows"] > 20
    assert payload["files"]["orders"]["rows"] > 0
    assert payload["files"]["trades"]["rows"] > 0


def test_backtest_inspection_script_fails_missing_artifact_directory(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing-backtest"
    completed = subprocess.run(
        [sys.executable, str(BACKTEST_SCRIPT), str(missing_dir)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode != 0
    assert payload["status"] == "FAIL"
    assert "artifact directory does not exist" in payload["blocking_issues"]
