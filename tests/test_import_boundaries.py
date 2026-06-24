import ast
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ALLOWED_THIRD_PARTY_ROOTS = {"numpy", "pandas"}
ALLOWED_QUANT_PREFIX = "quant.core.contract"


def test_import_linter_contracts_are_kept() -> None:
    lint_imports = Path(sys.executable).with_name("lint-imports")
    env = os.environ.copy()
    src_path = str(Path("src").resolve())
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (src_path, env.get("PYTHONPATH", "")) if part
    )
    completed = subprocess.run(
        [lint_imports],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_core_forbidden_contract_includes_live_runtime() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    contracts = config["tool"]["importlinter"]["contracts"]
    core_contract = next(
        contract
        for contract in contracts
        if contract["name"] == "core does not depend outward"
    )

    assert "quant.live" in core_contract["forbidden_modules"]


def test_strategy_imports_only_contract_and_allowed_libraries() -> None:
    for path in Path("strategies").glob("*.py"):
        if path.name == "__init__.py":
            continue
        forbidden = _forbidden_strategy_imports(path)
        assert forbidden == [], f"{path} imports forbidden module(s): {', '.join(forbidden)}"


def test_strategy_import_checker_rejects_non_allowed_third_party(tmp_path) -> None:
    strategy_path = tmp_path / "bad_strategy.py"
    strategy_path.write_text("import requests\n", encoding="utf-8")

    assert _forbidden_strategy_imports(strategy_path) == ["requests"]


def _forbidden_strategy_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_allowed_strategy_module(alias.name):
                    forbidden.append(alias.name)
        if isinstance(node, ast.ImportFrom):
            module = _import_from_module_name(node)
            if not _is_allowed_strategy_module(module):
                forbidden.append(module)
    return sorted(set(forbidden))


def _import_from_module_name(node: ast.ImportFrom) -> str:
    if node.level > 0:
        prefix = "." * node.level
        return prefix + (node.module or "")
    return node.module or ""


def _is_allowed_strategy_module(module: str) -> bool:
    if not module:
        return False
    if module == ALLOWED_QUANT_PREFIX or module.startswith(f"{ALLOWED_QUANT_PREFIX}."):
        return True
    if module.startswith("quant."):
        return False

    root = module.split(".", maxsplit=1)[0]
    return root in sys.stdlib_module_names or root in ALLOWED_THIRD_PARTY_ROOTS
