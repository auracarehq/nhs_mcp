"""Service layer for dm+d — maps API responses and manages the local cache."""

from __future__ import annotations

import json
import re

import db
from domains.dmd.client import get_product, search_products
from domains.dmd.models import DmdProductDetail, DmdProductSummary, DmdSearchResult

# Pattern to extract concept type from FSN parenthetical, e.g. "(product)" → "product"
_FSN_TYPE_RE = re.compile(r"\(([^)]+)\)\s*$")


def _extract_concept_type(fsn: str) -> str:
    m = _FSN_TYPE_RE.search(fsn)
    return m.group(1) if m else ""


def _bnf_code_from_fhir(raw: dict) -> str:
    """Extract BNF code from a FHIR Parameters/$lookup response if present."""
    for param in raw.get("parameter", []):
        if param.get("name") == "property":
            parts = {p["name"]: p.get("valueCode") or p.get("valueString", "") for p in param.get("part", [])}
            if parts.get("code") == "BNF":
                return str(parts.get("value", ""))
    return ""


async def search(term: str, limit: int = 25) -> DmdSearchResult:
    """Search dm+d products via Snowstorm ECL (live, not cached)."""
    raw = await search_products(term, limit)
    items = []
    for item in raw.get("items", []):
        fsn_term = item.get("fsn", {}).get("term", "") if isinstance(item.get("fsn"), dict) else ""
        items.append(DmdProductSummary(
            dmd_id=item.get("conceptId", ""),
            name=item.get("pt", {}).get("term", "") if isinstance(item.get("pt"), dict) else item.get("conceptId", ""),
            concept_type=_extract_concept_type(fsn_term),
        ))
    return DmdSearchResult(items=items, total=raw.get("total", len(items)))


async def fetch_and_cache(dmd_id: str) -> DmdProductDetail:
    """Force-fetch from NHS Terminology Server FHIR and write to local cache."""
    raw = await get_product(dmd_id)
    name = ""
    for param in raw.get("parameter", []):
        if param.get("name") == "display":
            name = param.get("valueString", "")
            break
    bnf_code = _bnf_code_from_fhir(raw)
    raw_str = json.dumps(raw)
    detail = DmdProductDetail(
        dmd_id=dmd_id,
        name=name,
        concept_type="",
        bnf_code=bnf_code,
        raw_json=raw_str,
        cached=True,
    )
    await db.cache_dmd_product(
        dmd_id=dmd_id,
        name=name,
        concept_type="",
        bnf_code=bnf_code,
        raw_json=raw_str,
    )
    return detail


async def get_or_fetch(dmd_id: str) -> DmdProductDetail:
    """Return from local cache if available; otherwise fetch and cache."""
    row = await db.get_dmd_product(dmd_id)
    if row:
        return DmdProductDetail(
            dmd_id=row["dmd_id"],
            name=row["name"],
            concept_type=row["concept_type"],
            bnf_code=row["bnf_code"],
            raw_json=row["raw_json"],
            cached=True,
        )
    return await fetch_and_cache(dmd_id)
