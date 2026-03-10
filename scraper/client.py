from __future__ import annotations

import asyncio

import httpx

from config import MAX_CONCURRENT, REQUEST_DELAY, USER_AGENT

_client: httpx.AsyncClient | None = None
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def get_client() -> httpx.AsyncClient:
    """Return the shared HTTP client instance."""
    assert _client is not None, "HTTP client not initialised — call init_client() first"
    return _client


def init_client() -> None:
    """Create the shared HTTP client."""
    global _client
    _client = httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    )


async def close_client() -> None:
    """Close and discard the shared HTTP client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def fetch(url: str) -> str:
    """Fetch a URL and return the response body as text."""
    client = get_client()
    async with _semaphore:
        resp = await client.get(url)
        resp.raise_for_status()
        await asyncio.sleep(REQUEST_DELAY)
        return resp.text
