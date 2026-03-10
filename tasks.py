from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TaskStatus:
    """In-memory representation of a background scrape task."""

    task_id: str
    status: str = "pending"  # pending | running | completed | failed | cancelled
    done: int = 0
    total: int = 0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict suitable for API responses."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "done": self.done,
            "total": self.total,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


_store: dict[str, TaskStatus] = {}
_async_tasks: dict[str, asyncio.Task] = {}
_active_scrapes: dict[str, str] = {}  # scrape_key -> task_id


def create_task() -> TaskStatus:
    """Create a new pending task and store it."""
    task = TaskStatus(task_id=uuid.uuid4().hex[:12])
    _store[task.task_id] = task
    return task


def register_async_task(task_id: str, async_task: asyncio.Task) -> None:
    """Associate an asyncio.Task with a task ID for cancellation support."""
    _async_tasks[task_id] = async_task


def get_active_scrape(scrape_key: str) -> TaskStatus | None:
    """Return the active task for a scrape key, or None if not running."""
    task_id = _active_scrapes.get(scrape_key)
    if task_id is None:
        return None
    task = _store.get(task_id)
    if task and task.status in ("pending", "running"):
        return task
    # Stale entry — clean up
    _active_scrapes.pop(scrape_key, None)
    return None


def set_active_scrape(scrape_key: str, task_id: str) -> None:
    """Mark a scrape key as active with the given task ID."""
    _active_scrapes[scrape_key] = task_id


def clear_active_scrape(scrape_key: str) -> None:
    """Remove a scrape key from the active set."""
    _active_scrapes.pop(scrape_key, None)


def cancel_task(task_id: str) -> bool:
    """Cancel a running task. Returns True if cancelled, False otherwise."""
    async_task = _async_tasks.get(task_id)
    if async_task is None or async_task.done():
        return False
    async_task.cancel()
    task = _store.get(task_id)
    if task:
        task.status = "cancelled"
        task.message = "Cancelled by user"
        task.updated_at = datetime.now(timezone.utc).isoformat()
    return True


def get_task(task_id: str) -> TaskStatus | None:
    """Look up a task by ID."""
    return _store.get(task_id)


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    done: int | None = None,
    total: int | None = None,
    message: str | None = None,
) -> None:
    """Update fields on an existing task."""
    task = _store.get(task_id)
    if task is None:
        return
    if status is not None:
        task.status = status
    if done is not None:
        task.done = done
    if total is not None:
        task.total = total
    if message is not None:
        task.message = message
    task.updated_at = datetime.now(timezone.utc).isoformat()
