"""Router for NHS Symptoms domain."""

from __future__ import annotations

import asyncio

import db
from domains.models import TaskResponse
from domains.nhs.models import ItemContent, ItemSummary
from domains.nhs.service import scrape_all, scrape_one, update_stale
from fastapi import APIRouter, HTTPException
from tasks import create_task, get_active_scrape, register_async_task, set_active_scrape

DOMAIN = "symptoms"
LABEL = "Symptoms"

router = APIRouter(prefix="/symptoms", tags=[LABEL])


@router.post("/scrape", response_model=TaskResponse, summary=f"Scrape all {LABEL}")
async def scrape_all_symptoms(force: bool = False) -> TaskResponse:
    """Start a background task that scrapes every item from the NHS Symptoms A-Z index."""
    scrape_key = f"{DOMAIN}:all"
    existing = get_active_scrape(scrape_key)
    if existing:
        raise HTTPException(409, detail={"message": f"A scrape for {LABEL} is already running", "task_id": existing.task_id})
    task = create_task()
    set_active_scrape(scrape_key, task.task_id)
    async_task = asyncio.create_task(scrape_all(DOMAIN, task.task_id, scrape_key, force=force))
    register_async_task(task.task_id, async_task)
    return TaskResponse(task_id=task.task_id)


@router.post("/scrape/{slug}", response_model=TaskResponse, summary="Scrape a single symptom")
async def scrape_one_symptom(slug: str) -> TaskResponse:
    """Start a background task that scrapes one symptom by slug."""
    scrape_key = f"{DOMAIN}:{slug}"
    existing = get_active_scrape(scrape_key)
    if existing:
        raise HTTPException(409, detail={"message": f"A scrape for {slug} is already running", "task_id": existing.task_id})
    task = create_task()
    set_active_scrape(scrape_key, task.task_id)
    async_task = asyncio.create_task(scrape_one(DOMAIN, slug, task.task_id, scrape_key))
    register_async_task(task.task_id, async_task)
    return TaskResponse(task_id=task.task_id)


@router.post("/update", response_model=TaskResponse, summary=f"Update stale {LABEL}")
async def update_stale_symptoms() -> TaskResponse:
    """Re-scrape all Symptoms whose next_review_due date has passed."""
    scrape_key = f"{DOMAIN}:update"
    existing = get_active_scrape(scrape_key)
    if existing:
        raise HTTPException(409, detail={"message": f"An update for {LABEL} is already running", "task_id": existing.task_id})
    task = create_task()
    set_active_scrape(scrape_key, task.task_id)
    async_task = asyncio.create_task(update_stale(DOMAIN, task.task_id, scrape_key))
    register_async_task(task.task_id, async_task)
    return TaskResponse(task_id=task.task_id)


@router.get("/", response_model=list[ItemSummary], summary=f"List scraped {LABEL}")
async def list_symptoms() -> list[ItemSummary]:
    """List all previously scraped Symptoms."""
    pool = db.get_pool()
    rows = await db.list_pages(pool, DOMAIN)
    return [ItemSummary(slug=r["slug"], name=r["name"]) for r in rows]


@router.get("/{slug}", response_model=ItemContent, summary="Get a scraped symptom")
async def get_symptom(slug: str) -> ItemContent:
    """Retrieve the full markdown content and metadata for a single symptom."""
    pool = db.get_pool()
    row = await db.get_page(pool, DOMAIN, slug)
    if row is None:
        raise HTTPException(404, f"{slug} not found")
    return ItemContent(
        slug=row["slug"], name=row["name"], url=row["url"],
        page_last_reviewed=row["page_last_reviewed"],
        next_review_due=row["next_review_due"], markdown=row["markdown"],
    )


@router.delete("/{slug}", summary="Delete a scraped symptom")
async def delete_symptom(slug: str) -> dict:
    """Remove a scraped symptom from the database."""
    pool = db.get_pool()
    deleted = await db.delete_page(pool, DOMAIN, slug)
    if not deleted:
        raise HTTPException(404, f"{slug} not found")
    return {"deleted": slug}
