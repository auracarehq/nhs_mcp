"""Helpers for style tests that analyse Python source files."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Directories containing production source code (not tests).
SOURCE_DIRS = [ROOT]
SOURCE_PACKAGES = [ROOT / "domains", ROOT / "scraper"]

# Limits
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 80
MAX_NESTING_DEPTH = 4
MAX_PARAMETERS = 6
MAX_CYCLOMATIC_COMPLEXITY = 18

# Exemptions: {function_name: set_of_skipped_checks}
EXEMPTIONS: dict[str, set[str]] = {
    "upsert_page": {"params"},  # Maps directly to DB columns
}


@dataclass
class SourceFile:
    path: Path
    relpath: str
    source: str
    tree: ast.AST
    lines: list[str] = field(default_factory=list)


def load_python_files() -> list[SourceFile]:
    """Load all production .py files (excluding tests/)."""
    files: list[SourceFile] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            d for d in dirnames if d not in {"tests", "__pycache__", ".git", "data", ".venv", "venv"}
        ]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            p = Path(dirpath) / fname
            source = p.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(p))
            except SyntaxError:
                continue
            lines = source.splitlines()
            files.append(SourceFile(
                path=p,
                relpath=str(p.relative_to(ROOT)),
                source=source,
                tree=tree,
                lines=lines,
            ))
    return files


def non_empty_non_comment_lines(lines: list[str]) -> int:
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def function_body_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count non-empty, non-comment, non-docstring lines in a function body."""
    if not node.body:
        return 0
    first = node.body[0]
    skip_docstring = (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
    )
    start_line = node.body[1].lineno if (skip_docstring and len(node.body) > 1) else node.body[0].lineno
    end_line = node.body[-1].end_lineno or node.body[-1].lineno
    return end_line - start_line + 1


def parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count parameters excluding 'self' and 'cls'."""
    args = node.args
    all_args = args.posonlyargs + args.args + args.kwonlyargs
    count = len(all_args)
    if all_args and all_args[0].arg in ("self", "cls"):
        count -= 1
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    return count


def _nesting_depth(node: ast.AST, current: int = 0) -> int:
    """Return the maximum nesting depth of control-flow statements."""
    max_depth = current
    nesting_types = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_types):
            max_depth = max(max_depth, _nesting_depth(child, current + 1))
        else:
            max_depth = max(max_depth, _nesting_depth(child, current))
    return max_depth


def nesting_depth(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return _nesting_depth(node)


def cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Approximate cyclomatic complexity."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            complexity += 1
        elif isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.Assert):
            complexity += 1
    return complexity


def iter_functions(tree: ast.AST):
    """Yield all top-level and method function/async-function defs."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def join_violations(violations: list[str]) -> str:
    return "\n".join(violations)
