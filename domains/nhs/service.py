"""Shared scrape orchestration for NHS domains."""

from __future__ import annotations

import asyncio
from datetime import datetime

import db
from domains.nhs.config import DOMAINS
from scraper.index import scrape_index
from scraper.markdown import page_to_markdown
from scraper.page import scrape_page
from tasks import clear_active_scrape, update_task


async def scrape_all(domain: str, task_id: str, scrape_key: str, *, force: bool = False) -> None:
    """Scrape every item from an NHS A-Z index."""
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", message="Fetching index...")
        entries = await scrape_index(cfg["index_url"])
        update_task(task_id, total=len(entries), message=f"Found {len(entries)} items")

        skipped = 0
        pool = db.get_pool()
        for i, entry in enumerate(entries):
            if not force:
                existing = await db.get_page(pool, domain, entry.slug)
                if existing:
                    skipped += 1
                    update_task(task_id, done=i + 1, message=f"Skipped {entry.slug} (already exists)")
                    continue
            try:
                page_data = await scrape_page(entry.url, name=entry.name)
                md_content = page_to_markdown(page_data)
                await db.upsert_page(pool, domain, entry.slug, name=page_data.name, url=page_data.url, page_last_reviewed=page_data.page_last_reviewed or "", next_review_due=page_data.next_review_due or "", markdown=md_content)
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
        pass
    except Exception as exc:
        update_task(task_id, status="failed", message=str(exc))
    finally:
        clear_active_scrape(scrape_key)


async def scrape_one(domain: str, slug: str, task_id: str, scrape_key: str) -> None:
    """Scrape a single item by slug."""
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", total=1, message=f"Scraping {slug}...")
        url = cfg["index_url"].rstrip("/") + f"/{slug}/"
        page_data = await scrape_page(url, name=slug)
        md_content = page_to_markdown(page_data)
        pool = db.get_pool()
        await db.upsert_page(pool, domain, slug, name=page_data.name, url=page_data.url, page_last_reviewed=page_data.page_last_reviewed or "", next_review_due=page_data.next_review_due or "", markdown=md_content)
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


async def _find_stale_pages(domain: str) -> list[tuple[str, str]]:
    """Return (slug, url) pairs for DB rows past their next_review_due date."""
    from sqlalchemy import select
    from db import ScrapedPage, get_session

    async with get_session() as session:
        result = await session.execute(
            select(ScrapedPage.slug, ScrapedPage.url, ScrapedPage.next_review_due)
            .where(ScrapedPage.domain == domain)
        )
        rows = result.all()
    now = datetime.now()
    stale: list[tuple[str, str]] = []
    for row in rows:
        if not row.next_review_due:
            continue
        due_date = _parse_review_date(str(row.next_review_due))
        if due_date and due_date < now:
            stale.append((row.slug, row.url))
    return stale


async def update_stale(domain: str, task_id: str, scrape_key: str) -> None:
    """Re-scrape pages whose review date has passed."""
    cfg = DOMAINS[domain]
    try:
        update_task(task_id, status="running", message="Scanning for stale pages...")
        stale = await _find_stale_pages(domain)

        if not stale:
            update_task(task_id, status="completed", done=0, total=0, message="No stale pages found")
            return

        update_task(task_id, total=len(stale), message=f"Found {len(stale)} stale pages")

        pool = db.get_pool()
        for i, (slug, url) in enumerate(stale):
            if not url:
                url = cfg["index_url"].rstrip("/") + f"/{slug}/"
            try:
                page_data = await scrape_page(url, name=slug)
                md_content = page_to_markdown(page_data)
                await db.upsert_page(pool, domain, slug, name=page_data.name, url=page_data.url, page_last_reviewed=page_data.page_last_reviewed or "", next_review_due=page_data.next_review_due or "", markdown=md_content)
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
