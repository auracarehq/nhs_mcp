"""Enforce complexity limits on Python source files."""

from tests.style.conftest import (
    EXEMPTIONS,
    MAX_CYCLOMATIC_COMPLEXITY,
    MAX_FILE_LINES,
    MAX_FUNCTION_LINES,
    MAX_NESTING_DEPTH,
    MAX_PARAMETERS,
    cyclomatic_complexity,
    function_body_lines,
    iter_functions,
    join_violations,
    load_python_files,
    nesting_depth,
    non_empty_non_comment_lines,
    parameter_count,
)


def test_files_stay_focused():
    violations = []
    for sf in load_python_files():
        count = non_empty_non_comment_lines(sf.lines)
        if count > MAX_FILE_LINES:
            violations.append(f"{sf.relpath}: {count} non-trivial lines (max {MAX_FILE_LINES})")
    assert not violations, "Files exceed line limit:\n" + join_violations(violations)


def test_functions_stay_small_and_shallow():
    violations = []
    for sf in load_python_files():
        for func in iter_functions(sf.tree):
            name = func.name
            exempted = EXEMPTIONS.get(name, set())

            if "length" not in exempted:
                length = function_body_lines(func)
                if length > MAX_FUNCTION_LINES:
                    violations.append(
                        f"{sf.relpath}:{func.lineno} {name}: {length} body lines (max {MAX_FUNCTION_LINES})"
                    )

            if "nesting" not in exempted:
                depth = nesting_depth(func)
                if depth > MAX_NESTING_DEPTH:
                    violations.append(
                        f"{sf.relpath}:{func.lineno} {name}: nesting depth {depth} (max {MAX_NESTING_DEPTH})"
                    )

            if "params" not in exempted:
                params = parameter_count(func)
                if params > MAX_PARAMETERS:
                    violations.append(
                        f"{sf.relpath}:{func.lineno} {name}: {params} parameters (max {MAX_PARAMETERS})"
                    )

            if "complexity" not in exempted:
                cc = cyclomatic_complexity(func)
                if cc > MAX_CYCLOMATIC_COMPLEXITY:
                    violations.append(
                        f"{sf.relpath}:{func.lineno} {name}: cyclomatic complexity {cc} (max {MAX_CYCLOMATIC_COMPLEXITY})"
                    )

    assert not violations, "Function complexity violations:\n" + join_violations(violations)
