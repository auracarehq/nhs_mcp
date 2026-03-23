"""ICD-11 response models."""

from __future__ import annotations

from pydantic import BaseModel


class IcdConceptSummary(BaseModel):
    """A summary of an ICD-11 concept from a search result."""

    entity_id: str
    icd_code: str
    title: str
    is_leaf: bool = False
    score: float | None = None


class IcdConceptDetail(IcdConceptSummary):
    """Full ICD-11 concept with definition and cache metadata."""

    definition: str = ""
    raw_json: str = ""
    cached: bool = False


class IcdSearchResult(BaseModel):
    """Paginated ICD-11 search results."""

    items: list[IcdConceptSummary]
    total: int
