"""Enforce layer boundaries between modules."""

import ast

from tests.style.conftest import join_violations, load_python_files

LAYER_RULES: list[tuple[str, list[str], str]] = [
    # (file prefix, forbidden import prefixes, reason)
    ("scraper/", ["domains", "tasks", "main"], "scraper must not import from domains, tasks, or main"),
    ("domains/models.py", ["scraper", "db", "tasks", "main"], "shared domain models must stay dependency-free"),
    ("domains/nhs/config.py", ["scraper", "db", "tasks", "main"], "NHS config must stay dependency-free"),
    ("domains/nice/config.py", ["scraper", "db", "tasks", "main"], "NICE config must stay dependency-free"),
    ("domains/mhra/config.py", ["scraper", "db", "tasks", "main"], "MHRA config must stay dependency-free"),
    ("domains/snomed/models.py", ["scraper", "db", "tasks", "main"], "SNOMED models must stay dependency-free"),
    ("domains/snomed/config.py", ["scraper", "db", "tasks", "main"], "SNOMED config must stay dependency-free"),
    ("domains/open_prescribing/config.py", ["scraper", "db", "tasks", "main"], "OpenPrescribing config must stay dependency-free"),
    ("domains/open_prescribing/models.py", ["scraper", "db", "tasks", "main"], "OpenPrescribing models must stay dependency-free"),
    ("domains/icd/config.py", ["scraper", "db", "tasks", "main"], "ICD-11 config must stay dependency-free"),
    ("domains/icd/models.py", ["scraper", "db", "tasks", "main"], "ICD-11 models must stay dependency-free"),
    ("domains/dmd/config.py", ["scraper", "db", "tasks", "main"], "dm+d config must stay dependency-free"),
    ("domains/dmd/models.py", ["scraper", "db", "tasks", "main"], "dm+d models must stay dependency-free"),
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
