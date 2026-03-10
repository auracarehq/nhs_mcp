"""Enforce layer boundaries between modules."""

import ast

from tests.style.conftest import join_violations, load_python_files

LAYER_RULES: list[tuple[str, list[str], str]] = [
    # (file prefix, forbidden import prefixes, reason)
    ("scraper/", ["domains", "tasks", "main"], "scraper must not import from domains, tasks, or main"),
    ("domains/models.py", ["scraper", "db", "tasks", "main"], "domain models must stay dependency-free"),
    ("domains/nhs/models.py", ["scraper", "db", "tasks", "main"], "NHS models must stay dependency-free"),
    ("domains/nhs/config.py", ["scraper", "db", "tasks", "main"], "NHS config must stay dependency-free"),
]


def _get_imports(tree: ast.AST) -> list[str]:
    """Extract all imported module names from an AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_layer_boundaries_stay_clean():
    violations = []
    for sf in load_python_files():
        imports = _get_imports(sf.tree)
        for prefix, forbidden, reason in LAYER_RULES:
            if not sf.relpath.startswith(prefix):
                continue
            for imp in imports:
                top = imp.split(".")[0]
                if top in forbidden:
                    violations.append(f"{sf.relpath}: imports '{imp}' — {reason}")
    assert not violations, "Architecture violations:\n" + join_violations(violations)
