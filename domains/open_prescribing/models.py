"""OpenPrescribing response models."""

from __future__ import annotations

from pydantic import BaseModel


class BnfResult(BaseModel):
    """A BNF code search result from OpenPrescribing."""

    bnf_code: str
    name: str
    dmd_id: str | None = None
    is_generic: bool = False


class BnfSearchResponse(BaseModel):
    """Paginated BNF search results."""

    items: list[BnfResult]
    total: int


class SpendingItem(BaseModel):
    """A single monthly spending data point."""

    date: str
    bnf_name: str
    actual_cost: float
    net_cost: float
    quantity: float
    total_items: int


class SpendingResponse(BaseModel):
    """Spending data for a BNF code."""

    bnf_code: str
    items: list[SpendingItem]


class SpendingByOrgItem(BaseModel):
    """Spending for a BNF code broken down by organisation."""

    row_id: str
    row_name: str
    date: str
    actual_cost: float
    net_cost: float
    quantity: float
    total_items: int


class SpendingByOrgResponse(BaseModel):
    """Spending-by-organisation data for a BNF code."""

    bnf_code: str
    org_type: str
    items: list[SpendingByOrgItem]
