from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
CIO_SKILL = SKILLS_ROOT / "quant-cio-orchestrator" / "SKILL.md"
CIO_DOC = ROOT / "docs" / "agents" / "quant-cio-agent.md"
HOOKS_DOC = ROOT / "docs" / "agents" / "risk-authorization-hooks.md"
OPERATING_MODEL_DOC = ROOT / "docs" / "agents" / "quant-agent-operating-model.md"
PROMOTION_WORKFLOW_DOC = ROOT / "docs" / "agents" / "workflow-strategy-promotion.md"
AGENTS_DOC = ROOT / "AGENTS.md"
ORCHESTRATOR_UI = SKILLS_ROOT / "quant-cio-orchestrator" / "agents" / "openai.yaml"
CASES_PATH = ROOT / "tests" / "fixtures" / "quant_cio_pressure_cases.yaml"


FRONTMATTER_RE = re.compile(
    r"^---\s*\nname:\s*(?P<name>[-a-z0-9]+)\s*\n"
    r"description:\s*(?P<description>.+?)\n---\s*\n",
    re.DOTALL,
)


DECISION_PACKAGE_FIELDS = [
    "CIO Decision:",
    "Strategy opportunity:",
    "Recommended next action:",
    "Candidate strategies:",
    "Evidence reviewed:",
    "Experiments to run:",
    "Sub-agent routing:",
    "Improvement proposal:",
    "Risk authorization needed:",
    "Blocking issues:",
    "Default safe option:",
    "Not allowed:",
]


REQUIRED_DOC_LINKS = [
    "AGENTS.md",
    "docs/agents/quant-agent-operating-model.md",
    "docs/agents/workflow-strategy-promotion.md",
    "docs/agents/risk-authorization-hooks.md",
]


EXPECTED_HOOKS = [
    "Strategy approval hook",
    "Pre-trade hook",
    "RiskEngine.check_order",
    "Drawdown hook",
    "RiskEngine.on_equity",
    "Market-data hook",
    "RuntimeMonitor.check_market_data",
    "Gateway incident hook",
    "Promotion hook",
    "validate_m3b_signoff.py",
    "Capital expansion hook",
    "Strategy change hook",
]


REDUNDANT_CHINESE_READABILITY_TERMS = [
    "中文速读",
    "一句话解释",
    "量化总监智能体",
    "策略准入授权钩子",
    "交易前风控钩子",
    "回撤熔断钩子",
    "行情数据钩子",
    "网关事故钩子",
    "阶段晋级钩子",
    "资金扩容授权钩子",
    "策略变更授权钩子",
]


@pytest.fixture(scope="module")
def cases() -> dict:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def skill_text() -> str:
    return read_text(CIO_SKILL)


def combined_cio_text() -> str:
    return "\n".join(read_text(path) for path in [CIO_SKILL, CIO_DOC, HOOKS_DOC])


def score_prompt(prompt: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in prompt.lower())


def has_positive_unsafe_phrase(text: str, phrase: str) -> bool:
    negative_markers = ["不", "不能", "不得", "不可", "禁止", "阻塞", "拒绝", "冻结"]
    for match in re.finditer(re.escape(phrase), text):
        prefix = text[max(0, match.start() - 24) : match.start()]
        if not any(marker in prefix for marker in negative_markers):
            return True
    return False


def test_quant_cio_skill_frontmatter_is_discovery_safe(cases: dict) -> None:
    match = FRONTMATTER_RE.match(skill_text())
    assert match, "quant-cio-orchestrator has invalid frontmatter"
    assert match.group("name") == "quant-cio-orchestrator"
    description = match.group("description")
    assert description.startswith("Use when ")
    assert len(description) <= 500
    for term in cases["cio"]["description_terms"]:
        assert term in description


def test_quant_cio_required_documents_exist_and_are_linked() -> None:
    assert CIO_DOC.exists()
    assert HOOKS_DOC.exists()
    text = skill_text()
    for required_link in REQUIRED_DOC_LINKS:
        assert required_link in text


def test_quant_cio_decision_package_fields_exist() -> None:
    text = combined_cio_text()
    assert "Quant CIO Decision Package" in text
    for field in DECISION_PACKAGE_FIELDS:
        assert field in text


def test_continuous_strategy_improvement_loop_exists() -> None:
    text = combined_cio_text()
    for term in ["Monitor", "Diagnose", "Propose", "Validate", "Promote / Hold / Retire"]:
        assert term in text


def test_risk_authorization_hooks_are_defined() -> None:
    text = read_text(HOOKS_DOC)
    assert "授权的是风险边界，不是每笔交易" in text
    for hook in EXPECTED_HOOKS:
        assert hook in text
    assert "边界内自动执行" in text
    assert "边界外默认阻塞" in text


def test_redundant_chinese_readability_layer_is_not_loaded() -> None:
    text = combined_cio_text()
    for term in REDUNDANT_CHINESE_READABILITY_TERMS:
        assert term not in text


def test_orchestrator_ui_metadata_uses_stable_english_labels() -> None:
    metadata = yaml.safe_load(read_text(ORCHESTRATOR_UI))
    assert metadata["interface"]["display_name"] == "Quant CIO Orchestrator"
    assert metadata["interface"]["short_description"] == "Classify and route quant strategy system requests"


def test_required_safety_boundaries_exist(cases: dict) -> None:
    text = combined_cio_text()
    for boundary in cases["cio"]["boundary_terms"]:
        assert boundary in text


def test_positive_prompt_matrix_selects_quant_cio(cases: dict) -> None:
    keywords = cases["cio"]["selection_keywords"]
    for prompt in cases["cio"]["should_trigger"]:
        assert score_prompt(prompt, keywords) > 0, prompt


def test_negative_prompt_matrix_does_not_select_quant_cio(cases: dict) -> None:
    keywords = cases["cio"]["selection_keywords"]
    for prompt in cases["cio"]["should_not_trigger"]:
        assert score_prompt(prompt, keywords) == 0, prompt


@pytest.mark.parametrize(
    "case", yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["unsafe_prompts"]
)
def test_unsafe_prompt_pressure_cases_have_explicit_guardrails(case: dict) -> None:
    assert case["required_guardrail"] in combined_cio_text()


def test_navigation_docs_reference_quant_cio_and_hooks() -> None:
    agents_text = read_text(AGENTS_DOC)
    operating_text = read_text(OPERATING_MODEL_DOC)
    workflow_text = read_text(PROMOTION_WORKFLOW_DOC)

    assert "docs/agents/quant-cio-agent.md" in agents_text
    assert "docs/agents/risk-authorization-hooks.md" in agents_text
    assert "Quant CIO Agent" in operating_text
    assert "6 个子智能体之上的总监角色" in operating_text
    assert "Quant CIO" in workflow_text
    assert "分类和调度" in workflow_text


def test_docs_do_not_use_positive_dangerous_language() -> None:
    text = "\n".join(
        read_text(path)
        for path in [AGENTS_DOC, OPERATING_MODEL_DOC, PROMOTION_WORKFLOW_DOC, CIO_DOC, HOOKS_DOC, CIO_SKILL]
    )
    for phrase in ["允许自动实盘", "批准真钱交易", "代替人类决策"]:
        assert not has_positive_unsafe_phrase(text, phrase), phrase
