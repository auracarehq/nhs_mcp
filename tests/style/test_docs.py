"""Ensure public functions and classes have docstrings."""

import ast

from tests.style.conftest import join_violations, load_python_files

# Modules where public declarations must have docstrings.
ENFORCED_PREFIXES = [
    "domains/",
    "scraper/",
    "db.py",
    "tasks.py",
]


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    if not node.body:
        return False
    first = node.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)


def test_public_declarations_have_docstrings():
    violations = []
    for sf in load_python_files():
        if not any(sf.relpath.startswith(p) for p in ENFORCED_PREFIXES):
            continue
        for node in ast.iter_child_nodes(sf.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if not _has_docstring(node):
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    violations.append(f"{sf.relpath}:{node.lineno} public {kind} '{node.name}' missing docstring")

    assert not violations, "Missing docstrings:\n" + join_violations(violations)
