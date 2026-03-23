"""HTTP client for the OpenPrescribing public API."""

from __future__ import annotations

import json

from domains.open_prescribing.config import OP_API_BASE
from scraper.client import fetch


async def search_bnf(term: str) -> list[dict]:
    """Search BNF codes by name. Returns raw list from OpenPrescribing."""
    url = f"{OP_API_BASE}/bnf_code/?q={term}&format=json"
    body = await fetch(url)
    return json.loads(body)


async def get_spending(bnf_code: str) -> list[dict]:
    """Return monthly national spending data for a BNF code."""
    url = f"{OP_API_BASE}/spending/?code={bnf_code}&format=json"
    body = await fetch(url)
    return json.loads(body)


async def get_spending_by_org(bnf_code: str, org_type: str) -> list[dict]:
    """Return spending broken down by organisation for a BNF code."""
    url = f"{OP_API_BASE}/spending_by_org/?code={bnf_code}&org_type={org_type}&format=json"
    body = await fetch(url)
    return json.loads(body)
