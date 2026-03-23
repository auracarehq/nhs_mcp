"""HTTP clients for dm+d: Snowstorm ECL search + NHS Terminology Server FHIR lookup."""

from __future__ import annotations

import json
from urllib.parse import quote

from domains.dmd.config import (
    DMD_SYSTEM,
    MEDICINAL_PRODUCT_ECL,
    NHS_TS_FHIR_BASE,
    SNOWSTORM_BASE,
    UK_BRANCH_ENCODED,
)
from scraper.client import fetch


async def search_products(term: str, limit: int = 25) -> dict:
    """Search dm+d products via Snowstorm ECL (SNOMED CT UK Drug Extension)."""
    ecl = quote(MEDICINAL_PRODUCT_ECL)
    term_enc = quote(term)
    url = (
        f"{SNOWSTORM_BASE}/browser/{UK_BRANCH_ENCODED}/concepts"
        f"?ecl={ecl}&term={term_enc}&activeFilter=true&limit={limit}"
    )
    body = await fetch(url)
    return json.loads(body)


async def get_product(dmd_id: str) -> dict:
    """Look up a dm+d product by code via the NHS Terminology Server FHIR $lookup."""
    system_enc = quote(DMD_SYSTEM)
    url = f"{NHS_TS_FHIR_BASE}/CodeSystem/$lookup?system={system_enc}&code={dmd_id}"
    body = await fetch(url)
    return json.loads(body)
