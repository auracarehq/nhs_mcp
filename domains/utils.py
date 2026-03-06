from __future__ import annotations

from pathlib import Path

import yaml


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, fm, _ = text.split("---", 2)
        return yaml.safe_load(fm) or {}
    return {}
