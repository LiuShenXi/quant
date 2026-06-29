import ast
import sys
import tomllib
from pathlib import Path

ALLOWED_THIRD_PARTY_ROOTS = {"numpy", "pandas"}
ALLOWED_QUANT_PREFIX = "quant.core.contract"


def test_import_linter_contracts_are_kept() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    violations = []
    for contract in config["tool"]["importlinter"]["contracts"]:
        for source_module in contract["source_modules"]:
            for path, imported_module in _module_imports(source_module):
                for forbidden_module in contract["forbidden_modules"]:
                    if _module_matches(imported_module, forbidden_module):
                        violations.append(
                            f"{contract['name']}: {path} imports {imported_module}"
                        )

    assert violations == []


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


def _module_imports(source_module: str) -> list[tuple[Path, str]]:
    source_root = Path("src") / Path(*source_module.split("."))
    imports: list[tuple[Path, str]] = []
    for path in source_root.rglob("*.py"):
        module_name = _path_to_module(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((path, alias.name) for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append((path, _resolved_import_from_module(module_name, node)))
    return imports


def _import_from_module_name(node: ast.ImportFrom) -> str:
    if node.level > 0:
        prefix = "." * node.level
        return prefix + (node.module or "")
    return node.module or ""


def _path_to_module(path: Path) -> str:
    relative = path.with_suffix("").relative_to("src")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolved_import_from_module(current_module: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""

    package_parts = current_module.split(".")
    if not current_module.endswith(".__init__"):
        package_parts = package_parts[:-1]
    base_parts = package_parts[: max(0, len(package_parts) - node.level + 1)]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _module_matches(module: str, expected: str) -> bool:
    return module == expected or module.startswith(f"{expected}.")


def _is_allowed_strategy_module(module: str) -> bool:
    if not module:
        return False
    if module == ALLOWED_QUANT_PREFIX or module.startswith(f"{ALLOWED_QUANT_PREFIX}."):
        return True
    if module.startswith("quant."):
        return False

    root = module.split(".", maxsplit=1)[0]
    return root in sys.stdlib_module_names or root in ALLOWED_THIRD_PARTY_ROOTS
