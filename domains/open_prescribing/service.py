"""Service layer for OpenPrescribing — validates inputs and maps API responses."""

from __future__ import annotations

from domains.open_prescribing.client import get_spending, get_spending_by_org, search_bnf
from domains.open_prescribing.models import (
    BnfResult,
    BnfSearchResponse,
    SpendingByOrgItem,
    SpendingByOrgResponse,
    SpendingItem,
    SpendingResponse,
)

VALID_ORG_TYPES = {"ccg", "practice", "pcn", "sicbl", "regional_team"}


def _map_bnf_item(raw: dict) -> BnfResult:
    return BnfResult(
        bnf_code=raw.get("bnf_code", ""),
        name=raw.get("name", ""),
        dmd_id=raw.get("dmd_id") or None,
        is_generic=bool(raw.get("is_generic", False)),
    )


def _map_spending_item(raw: dict) -> SpendingItem:
    return SpendingItem(
        date=raw.get("date", ""),
        bnf_name=raw.get("bnf_name", ""),
        actual_cost=float(raw.get("actual_cost", 0)),
        net_cost=float(raw.get("net_cost", 0)),
        quantity=float(raw.get("quantity", 0)),
        total_items=int(raw.get("total_items", 0)),
    )


def _map_spending_by_org_item(raw: dict) -> SpendingByOrgItem:
    return SpendingByOrgItem(
        row_id=raw.get("row_id", ""),
        row_name=raw.get("row_name", ""),
        date=raw.get("date", ""),
        actual_cost=float(raw.get("actual_cost", 0)),
        net_cost=float(raw.get("net_cost", 0)),
        quantity=float(raw.get("quantity", 0)),
        total_items=int(raw.get("total_items", 0)),
    )


async def search(term: str) -> BnfSearchResponse:
    """Search BNF codes by name."""
    raw_items = await search_bnf(term)
    items = [_map_bnf_item(r) for r in raw_items]
    return BnfSearchResponse(items=items, total=len(items))


async def spending(bnf_code: str) -> SpendingResponse:
    """Return national monthly spending data for a BNF code."""
    raw_items = await get_spending(bnf_code)
    return SpendingResponse(
        bnf_code=bnf_code,
        items=[_map_spending_item(r) for r in raw_items],
    )


async def spending_by_org(bnf_code: str, org_type: str) -> SpendingByOrgResponse:
    """Return spending broken down by organisation for a BNF code."""
    if org_type not in VALID_ORG_TYPES:
        raise ValueError(f"org_type must be one of: {', '.join(sorted(VALID_ORG_TYPES))}")
    raw_items = await get_spending_by_org(bnf_code, org_type)
    return SpendingByOrgResponse(
        bnf_code=bnf_code,
        org_type=org_type,
        items=[_map_spending_by_org_item(r) for r in raw_items],
    )
