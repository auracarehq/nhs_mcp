"""Router for OpenPrescribing NHS prescribing analytics."""

from __future__ import annotations

from domains.open_prescribing.models import (
    BnfSearchResponse,
    SpendingByOrgResponse,
    SpendingResponse,
)
from domains.open_prescribing.service import VALID_ORG_TYPES, search, spending, spending_by_org
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/open-prescribing", tags=["OpenPrescribing"])


@router.get(
    "/bnf",
    response_model=BnfSearchResponse,
    summary="Search BNF codes",
    description=(
        "Search for BNF codes by drug name via the OpenPrescribing API. "
        "Results include the BNF code, display name, linked dm+d ID, and generic flag. "
        "This always calls the live API — results are not cached."
    ),
)
async def search_bnf(
    q: str = Query(..., min_length=2, description="Drug name or BNF code prefix to search for"),
) -> BnfSearchResponse:
    """Search BNF codes by drug name via OpenPrescribing."""
    try:
        return await search(q)
    except Exception as exc:
        raise HTTPException(502, f"OpenPrescribing API error: {exc}") from exc


@router.get(
    "/bnf/{bnf_code}/spending",
    response_model=SpendingResponse,
    summary="National monthly spending for a BNF code",
    description=(
        "Return monthly national spending data (actual cost, net cost, quantity, items) "
        "for a BNF code. Data comes directly from OpenPrescribing and is not cached."
    ),
)
async def get_spending(bnf_code: str) -> SpendingResponse:
    """Return national monthly spending data for a BNF code."""
    try:
        return await spending(bnf_code)
    except Exception as exc:
        raise HTTPException(502, f"OpenPrescribing API error: {exc}") from exc


@router.get(
    "/bnf/{bnf_code}/spending-by-org",
    response_model=SpendingByOrgResponse,
    summary="Spending for a BNF code broken down by organisation",
    description=(
        f"Return spending data broken down by organisation. "
        f"`org_type` must be one of: {', '.join(sorted(VALID_ORG_TYPES))}."
    ),
)
async def get_spending_by_org(
    bnf_code: str,
    org_type: str = Query("practice", description="Organisation type"),
) -> SpendingByOrgResponse:
    """Return spending broken down by organisation for a BNF code."""
    try:
        return await spending_by_org(bnf_code, org_type)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"OpenPrescribing API error: {exc}") from exc
