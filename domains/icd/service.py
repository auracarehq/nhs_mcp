"""Service layer for ICD-11 — maps WHO API responses and manages the local cache."""

from __future__ import annotations

import json

import db
from domains.icd.client import get_entity, search_icd11
from domains.icd.models import IcdConceptDetail, IcdConceptSummary, IcdSearchResult


def _entity_id_from_uri(uri: str) -> str:
    """Extract the numeric entity ID from a WHO ICD URI."""
    return uri.rstrip("/").split("/")[-1]


def _map_summary(item: dict) -> IcdConceptSummary:
    return IcdConceptSummary(
        entity_id=_entity_id_from_uri(item.get("@id", "")),
        icd_code=item.get("theCode", ""),
        title=item.get("title", {}).get("@value", "") if isinstance(item.get("title"), dict) else str(item.get("title", "")),
        is_leaf=bool(item.get("isLeaf", False)),
        score=item.get("score"),
    )


def _map_detail(entity_id: str, raw: dict, cached: bool = False) -> IcdConceptDetail:
    title = raw.get("title", {})
    if isinstance(title, dict):
        title = title.get("@value", "")
    definition = raw.get("definition", {})
    if isinstance(definition, dict):
        definition = definition.get("@value", "")
    icd_code = raw.get("code", "") or raw.get("codeRange", "") or ""
    return IcdConceptDetail(
        entity_id=entity_id,
        icd_code=icd_code,
        title=str(title),
        definition=str(definition),
        raw_json=json.dumps(raw),
        cached=cached,
    )


async def search(term: str) -> IcdSearchResult:
    """Live ICD-11 search — results are not cached."""
    raw = await search_icd11(term)
    items = [_map_summary(i) for i in raw.get("destinationEntities", [])]
    return IcdSearchResult(items=items, total=len(items))


async def fetch_and_cache(entity_id: str) -> IcdConceptDetail:
    """Force-fetch from the WHO API and write to the local cache."""
    raw = await get_entity(entity_id)
    detail = _map_detail(entity_id, raw, cached=True)
    await db.cache_icd11_concept(
        entity_id=detail.entity_id,
        icd_code=detail.icd_code,
        title=detail.title,
        definition=detail.definition,
        raw_json=detail.raw_json,
    )
    return detail


async def get_or_fetch(entity_id: str) -> IcdConceptDetail:
    """Return from local cache if available; otherwise fetch and cache."""
    row = await db.get_icd11_concept(entity_id)
    if row:
        return IcdConceptDetail(
            entity_id=row["entity_id"],
            icd_code=row["icd_code"],
            title=row["title"],
            definition=row["definition"],
            raw_json=row["raw_json"],
            cached=True,
        )
    return await fetch_and_cache(entity_id)
