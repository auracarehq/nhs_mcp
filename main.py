from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from domains.models import TaskStatusResponse
from domains.router import create_domain_router
from scraper.client import close_client, init_client
from tasks import get_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_client()
    yield
    await close_client()


app = FastAPI(
    title="NHS Health A-Z Scraper",
    description=(
        "Scrapes the NHS Health A-Z website and saves content as markdown files "
        "with YAML frontmatter. Covers Conditions, Symptoms, Medicines, and "
        "Tests & Treatments."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(create_domain_router("conditions", "conditions"))
app.include_router(create_domain_router("symptoms", "symptoms"))
app.include_router(create_domain_router("medicines", "medicines"))
app.include_router(create_domain_router("treatments", "treatments"))


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
