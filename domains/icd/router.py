"""Router for ICD-11 concept search and local caching."""

from __future__ import annotations

import os

import db
from domains.icd.models import IcdConceptDetail, IcdConceptSummary, IcdSearchResult
from domains.icd.service import fetch_and_cache, get_or_fetch, search
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/icd", tags=["ICD-11"])


def _require_credentials() -> None:
    if not os.environ.get("ICD_CLIENT_ID") or not os.environ.get("ICD_CLIENT_SECRET"):
        raise HTTPException(
            503,
            detail=(
                "ICD-11 API credentials not configured. "
                "Set ICD_CLIENT_ID and ICD_CLIENT_SECRET environment variables."
            ),
        )


@router.get(
    "/concepts",
    response_model=IcdSearchResult,
    summary="Search ICD-11 concepts",
    description=(
        "Search ICD-11 MMS (Mortality and Morbidity Statistics) by clinical term via the "
        "WHO ICD API. Requires ICD_CLIENT_ID and ICD_CLIENT_SECRET to be configured. "
        "Results are not cached — this always hits the live API."
    ),
)
async def search_concepts(
    q: str = Query(..., min_length=2, description="Clinical term to search for"),
) -> IcdSearchResult:
    """Search ICD-11 MMS by clinical term via the WHO API."""
    _require_credentials()
    try:
        return await search(q)
    except Exception as exc:
        raise HTTPException(502, f"ICD-11 API error: {exc}") from exc


@router.get(
    "/cached",
    response_model=list[IcdConceptSummary],
    summary="List locally cached ICD-11 concepts",
    description="Return all ICD-11 concepts stored in the local PostgreSQL cache.",
)
async def list_cached() -> list[IcdConceptSummary]:
    """List all ICD-11 concepts stored in the local cache."""
    rows = await db.list_icd11_concepts()
    return [
        IcdConceptSummary(
            entity_id=r["entity_id"],
            icd_code=r["icd_code"],
            title=r["title"],
        )
        for r in rows
    ]


@router.get(
    "/concepts/{entity_id}",
    response_model=IcdConceptDetail,
    summary="Get or fetch an ICD-11 concept",
    description=(
        "Return the concept from the local cache if available; otherwise fetch from "
        "the WHO ICD API, cache the result, and return it. "
        "Requires ICD_CLIENT_ID and ICD_CLIENT_SECRET."
    ),
)
async def get_concept(entity_id: str) -> IcdConceptDetail:
    """Fetch an ICD-11 concept from cache or live API."""
    _require_credentials()
    try:
        return await get_or_fetch(entity_id)
    except Exception as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.post(
    "/concepts/{entity_id}/cache",
    response_model=IcdConceptDetail,
    summary="Force-refresh an ICD-11 concept cache entry",
    description=(
        "Explicitly fetch from the WHO ICD API and overwrite the local cache entry. "
        "Requires ICD_CLIENT_ID and ICD_CLIENT_SECRET."
    ),
)
async def cache_concept(entity_id: str) -> IcdConceptDetail:
    """Force-fetch an ICD-11 concept from the WHO API and overwrite the cache."""
    _require_credentials()
    try:
        return await fetch_and_cache(entity_id)
    except Exception as exc:
        raise HTTPException(502, detail=str(exc)) from exc


@router.delete(
    "/concepts/{entity_id}",
    summary="Remove an ICD-11 concept from the local cache",
)
async def delete_concept(entity_id: str) -> dict:
    """Remove an ICD-11 concept from the local cache."""
    deleted = await db.delete_icd11_concept(entity_id)
    if not deleted:
        raise HTTPException(404, f"Concept {entity_id} not in cache")
    return {"deleted": entity_id}
