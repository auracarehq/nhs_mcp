"""Router for dm+d (Dictionary of Medicines and Devices) product lookup."""

from __future__ import annotations

import db
from domains.dmd.models import DmdProductDetail, DmdProductSummary, DmdSearchResult
from domains.dmd.service import fetch_and_cache, get_or_fetch, search
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/dmd", tags=["dm+d"])

_DEFAULT_LIMIT = 25
_MAX_LIMIT = 100


@router.get(
    "/products",
    response_model=DmdSearchResult,
    summary="Search dm+d products",
    description=(
        "Search for dm+d (Dictionary of Medicines and Devices) products by name via the "
        "SNOMED CT UK Drug Extension through the public Snowstorm API. "
        "Results are not cached — this always hits the live API."
    ),
)
async def search_products(
    q: str = Query(..., min_length=2, description="Drug or device name to search for"),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
) -> DmdSearchResult:
    """Search dm+d products via Snowstorm ECL."""
    try:
        return await search(q, limit)
    except Exception as exc:
        raise HTTPException(502, f"dm+d search error: {exc}") from exc


@router.get(
    "/cached",
    response_model=list[DmdProductSummary],
    summary="List locally cached dm+d products",
    description="Return all dm+d products stored in the local PostgreSQL cache.",
)
async def list_cached() -> list[DmdProductSummary]:
    """List all dm+d products stored in the local cache."""
    rows = await db.list_dmd_products()
    return [
        DmdProductSummary(
            dmd_id=r["dmd_id"],
            name=r["name"],
            concept_type=r["concept_type"],
        )
        for r in rows
    ]


@router.get(
    "/products/{dmd_id}",
    response_model=DmdProductDetail,
    summary="Get or fetch a dm+d product",
    description=(
        "Return the product from the local cache if available; otherwise fetch from "
        "the NHS Terminology Server FHIR API, cache the result, and return it."
    ),
)
async def get_product(dmd_id: str) -> DmdProductDetail:
    """Fetch a dm+d product from cache or the NHS Terminology Server."""
    try:
        return await get_or_fetch(dmd_id)
    except Exception as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.post(
    "/products/{dmd_id}/cache",
    response_model=DmdProductDetail,
    summary="Force-refresh a dm+d product cache entry",
    description="Explicitly fetch from the NHS Terminology Server FHIR API and overwrite the local cache entry.",
)
async def cache_product(dmd_id: str) -> DmdProductDetail:
    """Force-fetch a dm+d product from NHS Terminology Server and overwrite the cache."""
    try:
        return await fetch_and_cache(dmd_id)
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc


@router.delete(
    "/products/{dmd_id}",
    summary="Remove a dm+d product from the local cache",
)
async def delete_product(dmd_id: str) -> dict:
    """Remove a dm+d product from the local cache."""
    deleted = await db.delete_dmd_product(dmd_id)
    if not deleted:
        raise HTTPException(404, f"Product {dmd_id} not in cache")
    return {"deleted": dmd_id}
