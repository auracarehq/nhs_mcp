from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TaskStatus:
    task_id: str
    status: str = "pending"  # pending | running | completed | failed
    done: int = 0
    total: int = 0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
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


def create_task() -> TaskStatus:
    task = TaskStatus(task_id=uuid.uuid4().hex[:12])
    _store[task.task_id] = task
    return task


def get_task(task_id: str) -> TaskStatus | None:
    return _store.get(task_id)


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    done: int | None = None,
    total: int | None = None,
    message: str | None = None,
) -> None:
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
