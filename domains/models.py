"""Shared response models used across domains."""

from __future__ import annotations

from pydantic import BaseModel


class TaskResponse(BaseModel):
    """Response returned when a background task is created."""

    task_id: str


class TaskStatusResponse(BaseModel):
    """Full status of a background task."""

    task_id: str
    status: str
    done: int
    total: int
    message: str
    created_at: str
    updated_at: str


class SearchResult(BaseModel):
    """A single search result with domain context."""

    slug: str
    name: str
    domain: str
