from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path


from domains.utils import read_frontmatter
from fastapi import APIRouter, HTTPException

from config import DOMAINS
from domains.models import ItemContent, ItemSummary, TaskResponse
from scraper.index import scrape_index
from scraper.markdown import page_to_markdown, save_markdown
from scraper.page import scrape_page
from tasks import (
    clear_active_scrape,
    create_task,
    get_active_scrape,
    register_async_task,
    set_active_scrape,
    update_task,
)




async def _scrape_all(domain: str, task_id: str, scrape_key: str, *, force: bool = False) -> None:
    cfg = DOMAINS[domain]
    data_dir: Path = cfg["data_dir"]
    try:
        update_task(task_id, status="running", message="Fetching index...")
        entries = await scrape_index(cfg["index_url"])
        update_task(task_id, total=len(entries), message=f"Found {len(entries)} items")

        skipped = 0
        for i, entry in enumerate(entries):
            if not force and (data_dir / f"{entry.slug}.md").exists():
                skipped += 1
                update_task(task_id, done=i + 1, message=f"Skipped {entry.slug} (already exists)")
                continue
            try:
                page_data = await scrape_page(entry.url, name=entry.name)
                md_content = page_to_markdown(page_data)
                save_markdown(md_content, data_dir, entry.slug)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                update_task(task_id, message=f"Error on {entry.slug}: {exc}")
            update_task(task_id, done=i + 1)

        msg = "Done"
        if skipped:
            msg = f"Done ({skipped} skipped, already existed)"
        update_task(task_id, status="completed", message=msg)
    except asyncio.CancelledError:
        pass  # status already set by cancel_task()
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))
    finally:
        clear_active_scrape(scrape_key)


async def _scrape_one(domain: str, slug: str, task_id: str, scrape_key: str) -> None:
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", total=1, message=f"Scraping {slug}...")
        url = cfg["index_url"].rstrip("/") + f"/{slug}/"
        page_data = await scrape_page(url, name=slug)
        md_content = page_to_markdown(page_data)
        save_markdown(md_content, cfg["data_dir"], slug)
        update_task(task_id, status="completed", done=1, message="Done")
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))
    finally:
        clear_active_scrape(scrape_key)


def _parse_review_date(date_str: str) -> datetime | None:
    """Parse NHS review date strings like '03 January 2023'."""
    for fmt in ("%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _find_stale_files(data_dir: Path) -> list[tuple[str, str]]:
    """Return (slug, url) pairs for files past their next_review_due date."""
    if not data_dir.exists():
        return []
    now = datetime.now()
    stale: list[tuple[str, str]] = []
    for path in sorted(data_dir.glob("*.md")):
        fm = read_frontmatter(path)
        review_due = fm.get("next_review_due", "")
        if not review_due:
            continue
        due_date = _parse_review_date(str(review_due))
        if due_date and due_date < now:
            stale.append((path.stem, fm.get("url", "")))
    return stale


async def _update_stale(domain: str, task_id: str, scrape_key: str) -> None:
    cfg = DOMAINS[domain]
    data_dir: Path = cfg["data_dir"]
    try:
        update_task(task_id, status="running", message="Scanning for stale pages...")
        stale = _find_stale_files(data_dir)

        if not stale:
            update_task(task_id, status="completed", done=0, total=0, message="No stale pages found")
            return

        update_task(task_id, total=len(stale), message=f"Found {len(stale)} stale pages")

        for i, (slug, url) in enumerate(stale):
            if not url:
                url = cfg["index_url"].rstrip("/") + f"/{slug}/"
            try:
                page_data = await scrape_page(url, name=slug)
                md_content = page_to_markdown(page_data)
                save_markdown(md_content, data_dir, slug)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                update_task(task_id, message=f"Error on {slug}: {exc}")
            update_task(task_id, done=i + 1)

        update_task(task_id, status="completed", message=f"Done (updated {len(stale)} stale pages)")
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))
    finally:
        clear_active_scrape(scrape_key)


def create_domain_router(domain: str, prefix: str) -> APIRouter:
    label = domain.replace("_", " ").title()
    router = APIRouter(prefix=f"/{prefix}", tags=[label])
    cfg = DOMAINS[domain]

    @router.post(
        "/scrape",
        response_model=TaskResponse,
        summary=f"Scrape all {label}",
        description=(
            f"Start a background task that scrapes every item from the NHS {label} A-Z index. "
            f"By default, items that have already been scraped are skipped. "
            f"Set `force=true` to re-scrape and overwrite all existing files. "
            f"Returns 409 if a scrape for this domain is already running."
        ),
    )
    async def scrape_all(force: bool = False) -> TaskResponse:
        scrape_key = f"{domain}:all"
        existing = get_active_scrape(scrape_key)
        if existing:
            raise HTTPException(409, detail={
                "message": f"A scrape for {label} is already running",
                "task_id": existing.task_id,
            })
        task = create_task()
        set_active_scrape(scrape_key, task.task_id)
        async_task = asyncio.create_task(_scrape_all(domain, task.task_id, scrape_key, force=force))
        register_async_task(task.task_id, async_task)
        return TaskResponse(task_id=task.task_id)

    @router.post(
        "/scrape/{slug}",
        response_model=TaskResponse,
        summary=f"Scrape a single {domain.rstrip('s')}",
        description=(
            f"Start a background task that scrapes one {domain.rstrip('s')} by slug. "
            f"Always overwrites the existing file if present. "
            f"Returns 409 if this item is already being scraped."
        ),
    )
    async def scrape_one(slug: str) -> TaskResponse:
        scrape_key = f"{domain}:{slug}"
        existing = get_active_scrape(scrape_key)
        if existing:
            raise HTTPException(409, detail={
                "message": f"A scrape for {slug} is already running",
                "task_id": existing.task_id,
            })
        task = create_task()
        set_active_scrape(scrape_key, task.task_id)
        async_task = asyncio.create_task(_scrape_one(domain, slug, task.task_id, scrape_key))
        register_async_task(task.task_id, async_task)
        return TaskResponse(task_id=task.task_id)

    @router.post(
        "/update",
        response_model=TaskResponse,
        summary=f"Update stale {label}",
        description=(
            f"Start a background task that re-scrapes all {label} whose "
            f"`next_review_due` date has passed. Only affects previously scraped items. "
            f"Returns 409 if an update for this domain is already running."
        ),
    )
    async def update_stale() -> TaskResponse:
        scrape_key = f"{domain}:update"
        existing = get_active_scrape(scrape_key)
        if existing:
            raise HTTPException(409, detail={
                "message": f"An update for {label} is already running",
                "task_id": existing.task_id,
            })
        task = create_task()
        set_active_scrape(scrape_key, task.task_id)
        async_task = asyncio.create_task(_update_stale(domain, task.task_id, scrape_key))
        register_async_task(task.task_id, async_task)
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
            fm = read_frontmatter(path)
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
        fm = read_frontmatter(path)
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
