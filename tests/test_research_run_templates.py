from __future__ import annotations

from pathlib import Path

import yaml

TEMPLATE_DIR = Path("research/templates")


def test_static_research_run_template_pack_is_complete() -> None:
    required_templates = {
        "run.yaml",
        "00_brief.md",
        "01_thesis.md",
        "02_data_requirements.md",
        "strategy_thesis.md",
        "data_audit.md",
        "03_experiment_plan.md",
        "risk_review.md",
        "paper_observation.md",
        "cio_decision_package.md",
        "07_decision_record.md",
        "research_run_README.md",
    }

    assert required_templates <= {
        path.name for path in TEMPLATE_DIR.iterdir() if path.is_file()
    }


def test_run_yaml_template_tracks_auditable_research_run_metadata() -> None:
    metadata = yaml.safe_load((TEMPLATE_DIR / "run.yaml").read_text(encoding="utf-8"))

    assert metadata["status"] == "THESIS_DRAFT"
    assert metadata["mode"] == "research-only"
    assert metadata["default_safe_action"] == "keep research-only"
    assert set(metadata) >= {
        "run_id",
        "created_at",
        "timezone",
        "topic",
        "research_type",
        "status",
        "mode",
        "related_strategies",
        "agents",
        "data_requirements",
        "experiment_plan",
        "decision_records",
        "blocking_issues",
        "not_allowed",
    }
    assert "real-money trading" in metadata["not_allowed"]


def test_daily_research_templates_keep_required_decision_fields() -> None:
    brief = (TEMPLATE_DIR / "00_brief.md").read_text(encoding="utf-8")
    experiment_plan = (TEMPLATE_DIR / "03_experiment_plan.md").read_text(
        encoding="utf-8"
    )
    data_requirements = (TEMPLATE_DIR / "02_data_requirements.md").read_text(
        encoding="utf-8"
    )
    decision_record = (TEMPLATE_DIR / "07_decision_record.md").read_text(
        encoding="utf-8"
    )

    for section in [
        "Run ID:",
        "Status: THESIS_DRAFT",
        "Data Requirements",
        "Experiment Plan",
        "Decision Record",
        "Default Safe Action",
        "Not Allowed",
    ]:
        assert section in brief

    for section in [
        "Status: DRAFT",
        "Intended Use",
        "Required Datasets",
        "Quality Requirements",
        "Reproducibility Requirements",
        "Known Gaps",
        "Data Audit Handoff",
    ]:
        assert section in data_requirements

    for section in [
        "Status: DESIGN_ONLY",
        "Data Inputs",
        "Baseline",
        "Experiment Matrix",
        "Pass Conditions",
        "Falsification Rules",
        "Reproducibility Notes",
    ]:
        assert section in experiment_plan

    for section in [
        "Decision:",
        "Evidence Reviewed",
        "Assumptions",
        "Blocking Issues",
        "Next Action",
        "Default Safe Action",
        "Not Allowed",
    ]:
        assert section in decision_record
