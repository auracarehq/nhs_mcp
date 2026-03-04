from pathlib import Path

from scraper.markdown import page_to_markdown, save_markdown
from scraper.page import PageData, Section


def test_page_to_markdown_single_section():
    page = PageData(
        name="Acne",
        url="https://www.nhs.uk/conditions/acne/",
        sections=[Section(title="", html="<p>Acne is common.</p>")],
        page_last_reviewed="03 January 2023",
        next_review_due="03 January 2026",
    )
    result = page_to_markdown(page)
    assert result.startswith("---\n")
    assert "name: Acne" in result
    assert "url: https://www.nhs.uk/conditions/acne/" in result
    assert "page_last_reviewed: 03 January 2023" in result
    assert "# Acne" in result
    assert "Acne is common." in result


def test_page_to_markdown_multi_section():
    page = PageData(
        name="Acne",
        url="https://www.nhs.uk/conditions/acne/",
        sections=[
            Section(title="Overview", html="<p>Overview text.</p>"),
            Section(title="Causes", html="<p>Causes text.</p>"),
        ],
    )
    result = page_to_markdown(page)
    assert "## Overview" in result
    assert "## Causes" in result
    assert "Overview text." in result
    assert "Causes text." in result


def test_save_markdown(tmp_path):
    content = "---\nname: test\n---\n# Test"
    path = save_markdown(content, tmp_path / "conditions", "test-item")
    assert path.exists()
    assert path.read_text() == content
    assert path.name == "test-item.md"


def test_save_markdown_creates_dirs(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    save_markdown("content", nested, "slug")
    assert (nested / "slug.md").exists()
