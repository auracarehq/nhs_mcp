"""dm+d response models."""

from __future__ import annotations

from pydantic import BaseModel


class DmdProductSummary(BaseModel):
    """A summary of a dm+d product from a search result."""

    dmd_id: str
    name: str
    concept_type: str = ""


class DmdProductDetail(DmdProductSummary):
    """Full dm+d product with BNF code, raw FHIR payload, and cache metadata."""

    bnf_code: str = ""
    raw_json: str = ""
    cached: bool = False


class DmdSearchResult(BaseModel):
    """Paginated dm+d product search results."""

    items: list[DmdProductSummary]
    total: int
