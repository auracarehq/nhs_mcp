from __future__ import annotations

from pathlib import Path

import yaml
from markdownify import markdownify as md

from scraper.page import PageData


def page_to_markdown(page: PageData) -> str:
    """Convert PageData to a markdown string with YAML frontmatter."""
    frontmatter = {
        "name": page.name,
        "url": page.url,
    }
    if page.page_last_reviewed:
        frontmatter["page_last_reviewed"] = page.page_last_reviewed
    if page.next_review_due:
        frontmatter["next_review_due"] = page.next_review_due

    parts = ["---", yaml.dump(frontmatter, default_flow_style=False).strip(), "---", ""]
    parts.append(f"# {page.name}")
    parts.append("")

    for section in page.sections:
        if section.title:
            parts.append(f"## {section.title}")
            parts.append("")

        converted = md(section.html, heading_style="ATX", strip=["img", "script", "style"])
        # Clean up excessive blank lines
        cleaned = "\n".join(
            line for i, line in enumerate(converted.split("\n"))
            if line.strip() or (i > 0 and converted.split("\n")[i - 1].strip())
        )
        parts.append(cleaned.strip())
        parts.append("")

    return "\n".join(parts)


def save_markdown(content: str, data_dir: Path, slug: str) -> Path:
    """Save markdown content to a file, creating directories as needed."""
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{slug}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path
