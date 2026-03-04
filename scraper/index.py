from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL
from scraper.client import fetch


@dataclass
class IndexEntry:
    name: str
    url: str
    slug: str


def parse_index(html: str, base_url: str = BASE_URL) -> list[IndexEntry]:
    """Parse an NHS A-Z index page and return all direct-link entries."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[IndexEntry] = []
    seen_slugs: set[str] = set()

    for a_tag in soup.select("main a[href]"):
        href = a_tag["href"]
        name = a_tag.get_text(strip=True)

        # Skip "Back to top", letter anchors, and cross-references ("see ...")
        if not name or not href.startswith("/") or href.startswith("/#"):
            continue

        # Build full URL and derive slug
        url = urljoin(base_url, href.rstrip("/") + "/")
        slug = href.strip("/").split("/")[-1]

        if slug and slug not in seen_slugs:
            seen_slugs.add(slug)
            entries.append(IndexEntry(name=name, url=url, slug=slug))

    return entries


async def scrape_index(index_url: str) -> list[IndexEntry]:
    html = await fetch(index_url)
    return parse_index(html)
