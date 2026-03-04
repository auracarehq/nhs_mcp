from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from config import DOMAINS
from domains.models import ItemContent, ItemSummary, TaskResponse
from scraper.index import scrape_index
from scraper.markdown import page_to_markdown, save_markdown
from scraper.page import scrape_page
from tasks import create_task, update_task


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, fm, _ = text.split("---", 2)
        return yaml.safe_load(fm) or {}
    return {}


async def _scrape_all(domain: str, task_id: str) -> None:
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", message="Fetching index...")
        entries = await scrape_index(cfg["index_url"])
        update_task(task_id, total=len(entries), message=f"Found {len(entries)} items")

        for i, entry in enumerate(entries):
            try:
                page_data = await scrape_page(entry.url, name=entry.name)
                md_content = page_to_markdown(page_data)
                save_markdown(md_content, cfg["data_dir"], entry.slug)
            except Exception as exc:
                update_task(task_id, message=f"Error on {entry.slug}: {exc}")
            update_task(task_id, done=i + 1)

        update_task(task_id, status="completed", message="Done")
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))


async def _scrape_one(domain: str, slug: str, task_id: str) -> None:
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", total=1, message=f"Scraping {slug}...")
        url = cfg["index_url"].rstrip("/") + f"/{slug}/"
        page_data = await scrape_page(url, name=slug)
        md_content = page_to_markdown(page_data)
        save_markdown(md_content, cfg["data_dir"], slug)
        update_task(task_id, status="completed", done=1, message="Done")
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))


def create_domain_router(domain: str, prefix: str) -> APIRouter:
    label = domain.replace("_", " ").title()
    router = APIRouter(prefix=f"/{prefix}", tags=[label])
    cfg = DOMAINS[domain]

    @router.post(
        "/scrape",
        response_model=TaskResponse,
        summary=f"Scrape all {label}",
        description=f"Start a background task that scrapes every item from the NHS {label} A-Z index. Returns a task_id to poll for progress.",
    )
    async def scrape_all() -> TaskResponse:
        task = create_task()
        asyncio.create_task(_scrape_all(domain, task.task_id))
        return TaskResponse(task_id=task.task_id)

    @router.post(
        "/scrape/{slug}",
        response_model=TaskResponse,
        summary=f"Scrape a single {domain.rstrip('s')}",
        description=f"Start a background task that scrapes one {domain.rstrip('s')} by slug. Returns a task_id to poll for progress.",
    )
    async def scrape_one(slug: str) -> TaskResponse:
        task = create_task()
        asyncio.create_task(_scrape_one(domain, slug, task.task_id))
        return TaskResponse(task_id=task.task_id)

    @router.get(
        "/",
        response_model=list[ItemSummary],
        summary=f"List scraped {label}",
        description=f"List all previously scraped {label} from the local cache. Returns slug and name for each item.",
    )
    async def list_items() -> list[ItemSummary]:
        data_dir: Path = cfg["data_dir"]
        if not data_dir.exists():
            return []
        items = []
        for path in sorted(data_dir.glob("*.md")):
            fm = _read_frontmatter(path)
            items.append(ItemSummary(
                slug=path.stem,
                name=fm.get("name", path.stem),
            ))
        return items

    @router.get(
        "/{slug}",
        response_model=ItemContent,
        summary=f"Get a scraped {domain.rstrip('s')}",
        description=f"Retrieve the full markdown content and metadata for a single scraped {domain.rstrip('s')}.",
    )
    async def get_item(slug: str) -> ItemContent:
        path: Path = cfg["data_dir"] / f"{slug}.md"
        if not path.exists():
            raise HTTPException(404, f"{slug} not found")
        text = path.read_text(encoding="utf-8")
        fm = _read_frontmatter(path)
        return ItemContent(
            slug=slug,
            name=fm.get("name", slug),
            url=fm.get("url", ""),
            page_last_reviewed=fm.get("page_last_reviewed", ""),
            next_review_due=fm.get("next_review_due", ""),
            markdown=text,
        )

    @router.delete(
        "/{slug}",
        summary=f"Delete a scraped {domain.rstrip('s')}",
        description=f"Remove a scraped {domain.rstrip('s')} markdown file from the local cache.",
    )
    async def delete_item(slug: str) -> dict:
        path: Path = cfg["data_dir"] / f"{slug}.md"
        if not path.exists():
            raise HTTPException(404, f"{slug} not found")
        path.unlink()
        return {"deleted": slug}

    return router
