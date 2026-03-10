"""Flag unreferenced private top-level functions and classes."""

import ast
import re

from tests.style.conftest import join_violations, load_python_files


def test_no_unreferenced_private_declarations():
    files = load_python_files()

    # Collect all private top-level function and class names with their locations.
    declarations: list[tuple[str, str, str]] = []  # (name, relpath, kind)
    for sf in files:
        for node in ast.iter_child_nodes(sf.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    declarations.append((node.name, sf.relpath, "function"))
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    declarations.append((node.name, sf.relpath, "class"))

    # Build a combined source of all files for reference checking.
    all_source = "\n".join(sf.source for sf in files)

    violations = []
    for name, relpath, kind in declarations:
        # Count occurrences — must appear more than once (the definition itself).
        count = len(re.findall(rf"\b{re.escape(name)}\b", all_source))
        if count <= 1:
            violations.append(f"{relpath}: unreferenced private {kind} '{name}'")

    assert not violations, "Dead code found:\n" + join_violations(violations)
