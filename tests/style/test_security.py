"""Detect obvious security anti-patterns in source code."""

import re

from tests.style.conftest import join_violations, load_python_files

SECURITY_PATTERNS = [
    (re.compile(r"\bsubprocess\b"), "subprocess usage"),
    (re.compile(r"\bos\.system\b"), "os.system usage"),
    (re.compile(r"\bos\.popen\b"), "os.popen usage"),
    (re.compile(r"\beval\s*\("), "eval() usage"),
    (re.compile(r"\bexec\s*\("), "exec() usage"),
    (re.compile(r"\b(?:md5|sha1)\b", re.IGNORECASE), "weak hash algorithm"),
    (re.compile(r"""(?:password|secret|api_key)\s*=\s*['"][^'"]+['"]""", re.IGNORECASE), "hardcoded credential"),
]


def test_no_obvious_security_anti_patterns():
    violations = []
    for sf in load_python_files():
        for i, line in enumerate(sf.lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, label in SECURITY_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{sf.relpath}:{i} {label}: {stripped[:80]}")
    assert not violations, "Security anti-patterns found:\n" + join_violations(violations)
