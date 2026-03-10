# Style Tests

This repository includes structural style tests under `tests/style/` that enforce
code quality and architectural boundaries using Python's `ast` module.

## Running

```bash
pytest tests/style/
```

## What The Style Tests Enforce

### Complexity and Module Focus

`test_complexity.py` checks that files and functions stay small and focused.

- Non-test Python files must stay under 260 non-empty, non-comment lines.
- Functions are checked for:
  - body length (≤ 80 lines)
  - nesting depth (≤ 4)
  - parameter count (≤ 6, excluding self/cls)
  - cyclomatic complexity (≤ 18)

### Architecture and Layer Boundaries

`test_architecture.py` protects module boundaries.

- `scraper/` must not import from `domains`, `tasks`, or `main`.
- `domains/models.py` must stay dependency-free (no `scraper`, `db`, `tasks`, `main`).
- `domains/utils.py` must stay dependency-free.

### Security Anti-Patterns

`test_security.py` scans for obvious unsafe patterns:

- `subprocess`, `os.system`, `os.popen`, `eval()`, `exec()`
- Weak hashes (`md5`, `sha1`)
- Hardcoded credentials (`password = "..."`, etc.)

### Dead Code

`test_dead_code.py` flags unreferenced private (`_`-prefixed) top-level functions
and classes.

### Docstrings

`test_docs.py` requires docstrings on public functions and classes in:

- `domains/`
- `scraper/`
- `db.py`
- `tasks.py`

## How To Work With These Rules

- Split large files instead of raising limits.
- Keep `scraper/` independent from application wiring.
- Add docstrings to public functions and classes in enforced modules.
- If a limit needs to change, update the constant in `tests/style/conftest.py`.
- Add exemptions for specific functions in `conftest.py` `EXEMPTIONS` dict.
