"""NHS-specific response models."""

from __future__ import annotations

from pydantic import BaseModel


class ItemSummary(BaseModel):
    """Slug and name of a scraped item."""

    slug: str
    name: str


class ItemContent(BaseModel):
    """Full content and metadata of a scraped item."""

    slug: str
    name: str
    url: str
    page_last_reviewed: str
    next_review_due: str
    markdown: str
