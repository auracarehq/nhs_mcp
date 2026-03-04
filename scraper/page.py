from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from config import BASE_URL
from scraper.client import fetch


@dataclass
class Section:
    title: str
    html: str


@dataclass
class PageData:
    name: str
    url: str
    sections: list[Section] = field(default_factory=list)
    page_last_reviewed: str = ""
    next_review_due: str = ""


def _extract_review_dates(soup: BeautifulSoup) -> tuple[str, str]:
    """Extract review dates from page footer text."""
    text = soup.get_text()
    last_match = re.search(r"Page last reviewed:\s*(.+?)(?:\n|$)", text)
    next_match = re.search(r"Next review due:\s*(.+?)(?:\n|$)", text)
    return (
        last_match.group(1).strip() if last_match else "",
        next_match.group(1).strip() if next_match else "",
    )


def _extract_content(soup: BeautifulSoup) -> str:
    """Extract the main article content HTML."""
    # Try common NHS content containers
    main = soup.find("main", id="maincontent") or soup.find("main")
    if main is None:
        main = soup.find("article") or soup.body or soup
    assert isinstance(main, Tag)

    # Remove navigation, header, footer elements from content
    for tag in main.find_all(["nav", "header", "footer"]):
        tag.decompose()

    # Remove the contents sidebar
    for heading in main.find_all("h2"):
        if heading.get_text(strip=True).lower() == "contents":
            parent = heading.parent
            if parent:
                parent.decompose()
            break

    return str(main)


def _find_tab_urls(soup: BeautifulSoup, page_url: str) -> list[tuple[str, str]]:
    """Find sub-page tab links (Overview, Causes, Treatment, etc.)."""
    tabs: list[tuple[str, str]] = []

    # Look for the contents navigation with an ordered list
    for ol in soup.find_all("ol"):
        parent = ol.parent
        if not parent:
            continue
        heading = parent.find("h2")
        if heading and heading.get_text(strip=True).lower() == "contents":
            for li in ol.find_all("li"):
                a = li.find("a")
                if a and a.get("href"):
                    title = a.get_text(strip=True)
                    url = urljoin(page_url, a["href"])
                    tabs.append((title, url))
                else:
                    # Current page (no link) — use the li text
                    title = li.get_text(strip=True)
                    tabs.append((title, page_url))
            break

    return tabs


def parse_page(html: str, url: str, section_title: str = "") -> tuple[str, str, str]:
    """Parse a single page. Returns (content_html, last_reviewed, next_review)."""
    soup = BeautifulSoup(html, "html.parser")
    content = _extract_content(soup)
    last_reviewed, next_review = _extract_review_dates(soup)
    return content, last_reviewed, next_review


async def scrape_page(url: str, name: str = "") -> PageData:
    """Fetch a page and all its sub-tabs, return combined PageData."""
    html = await fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    if not name:
        h1 = soup.find("h1")
        name = h1.get_text(strip=True) if h1 else url.split("/")[-2]

    tabs = _find_tab_urls(soup, url)

    page_data = PageData(name=name, url=url)

    if len(tabs) <= 1:
        # Single-page content (no tabs)
        content, last_reviewed, next_review = parse_page(html, url)
        page_data.sections.append(Section(title="", html=content))
        page_data.page_last_reviewed = last_reviewed
        page_data.next_review_due = next_review
    else:
        # Multi-tab page: fetch each tab
        for title, tab_url in tabs:
            if tab_url == url:
                tab_html = html
            else:
                tab_html = await fetch(tab_url)

            content, last_reviewed, next_review = parse_page(tab_html, tab_url)
            page_data.sections.append(Section(title=title, html=content))

            # Use review dates from the first tab that has them
            if last_reviewed and not page_data.page_last_reviewed:
                page_data.page_last_reviewed = last_reviewed
                page_data.next_review_due = next_review

    return page_data
