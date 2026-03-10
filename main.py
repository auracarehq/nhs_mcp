from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import db
from domains.models import SearchResult, TaskStatusResponse
from domains.nhs.conditions.router import router as conditions_router
from domains.nhs.medicines.router import router as medicines_router
from domains.nhs.symptoms.router import router as symptoms_router
from domains.nhs.treatments.router import router as treatments_router
from scraper.client import close_client, init_client
from tasks import cancel_task, get_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    init_client()
    yield
    await close_client()
    await db.close_db()


app = FastAPI(
    title="NHS Health A-Z Scraper",
    description=(
        "Scrapes the NHS Health A-Z website and stores content in PostgreSQL "
        "as markdown with YAML frontmatter. Covers Conditions, Symptoms, Medicines, and "
        "Tests & Treatments."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(conditions_router)
app.include_router(symptoms_router)
app.include_router(medicines_router)
app.include_router(treatments_router)


@app.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    tags=["tasks"],
    summary="Get task status",
    description="Poll a background scrape task for progress. Returns status (pending/running/completed/failed), items done/total, and a message.",
)
async def task_status(task_id: str) -> TaskStatusResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return TaskStatusResponse(**task.to_dict())


@app.post(
    "/tasks/{task_id}/cancel",
    tags=["tasks"],
    summary="Cancel a running task",
    description="Cancel a running background scrape task. Returns confirmation or 404 if the task doesn't exist, 409 if it's already finished.",
)
async def cancel_task_endpoint(task_id: str) -> dict:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(409, f"Task already {task.status}")
    cancel_task(task_id)
    return {"task_id": task_id, "status": "cancelled"}


@app.get(
    "/search",
    response_model=list[SearchResult],
    tags=["search"],
    summary="Search scraped content",
    description=(
        "Search for scraped items by name across all domains (conditions, symptoms, medicines, treatments). "
        "Only searches previously cached files. Returns an empty list for an empty query."
    ),
)
async def search(q: str = "") -> list[SearchResult]:
    if not q:
        return []
    pool = db.get_pool()
    rows = await db.search_pages(pool, q)
    return [SearchResult(slug=r["slug"], name=r["name"], domain=r["domain"]) for r in rows]
