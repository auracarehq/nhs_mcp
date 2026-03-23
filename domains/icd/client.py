"""HTTP client for the WHO ICD-11 API with OAuth2 token management."""

from __future__ import annotations

import json
import os
import time

from domains.icd.config import ICD_API_BASE, ICD_LINEARIZATION, ICD_RELEASE, ICD_TOKEN_URL
from scraper.client import fetch_with_headers, get_client

# Module-level token cache: {"access_token": str, "expires_at": float}
_token_cache: dict[str, object] = {}


async def _get_token() -> str:
    """Return a valid Bearer token, fetching a new one if needed."""
    now = time.time()
    cached = _token_cache.get("access_token")
    expires_at = _token_cache.get("expires_at", 0.0)
    if cached and now < float(expires_at) - 60:  # 60 s safety margin
        return str(cached)

    client_id = os.environ["ICD_CLIENT_ID"]
    client_secret = os.environ["ICD_CLIENT_SECRET"]
    http = get_client()
    resp = await http.post(
        ICD_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "icdapi_access",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    payload = resp.json()
    _token_cache["access_token"] = payload["access_token"]
    _token_cache["expires_at"] = now + payload.get("expires_in", 3600)
    return str(_token_cache["access_token"])


def _icd_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": "v2",
        "Accept-Language": "en",
    }


async def search_icd11(term: str) -> dict:
    """Search ICD-11 MMS by clinical term."""
    token = await _get_token()
    url = (
        f"{ICD_API_BASE}/icd/release/11/{ICD_RELEASE}/{ICD_LINEARIZATION}"
        f"/search?q={term}&flatResults=false"
    )
    body = await fetch_with_headers(url, _icd_headers(token))
    return json.loads(body)


async def get_entity(entity_id: str) -> dict:
    """Fetch a single ICD-11 entity by numeric ID."""
    token = await _get_token()
    url = f"{ICD_API_BASE}/icd/entity/{entity_id}"
    body = await fetch_with_headers(url, _icd_headers(token))
    return json.loads(body)
