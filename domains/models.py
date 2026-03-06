from __future__ import annotations

from pydantic import BaseModel


class TaskResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    done: int
    total: int
    message: str
    created_at: str
    updated_at: str


class ItemSummary(BaseModel):
    slug: str
    name: str


class ItemContent(BaseModel):
    slug: str
    name: str
    url: str
    page_last_reviewed: str
    next_review_due: str
    markdown: str


class SearchResult(BaseModel):
    slug: str
    name: str
    domain: str
