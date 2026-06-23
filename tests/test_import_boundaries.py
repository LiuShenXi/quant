import ast
import subprocess
import sys
from pathlib import Path


def test_import_linter_contracts_are_kept() -> None:
    lint_imports = Path(sys.executable).with_name("lint-imports")
    completed = subprocess.run([lint_imports], check=False, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_strategy_imports_only_contract_and_allowed_libraries() -> None:
    allowed_roots = {"numpy", "pandas", "quant.core.contract"}
    for path in Path("strategies").glob("*.py"):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("quant.")
                and not node.module.startswith("quant.core.contract")
            ):
                raise AssertionError(f"{path} imports forbidden module {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("quant.") and alias.name not in allowed_roots:
                        raise AssertionError(f"{path} imports forbidden module {alias.name}")
