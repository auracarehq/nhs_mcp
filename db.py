from __future__ import annotations

import os

import asyncpg

_pool: asyncpg.Pool | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scraped_pages (
    domain             TEXT        NOT NULL,
    slug               TEXT        NOT NULL,
    name               TEXT        NOT NULL,
    url                TEXT        NOT NULL DEFAULT '',
    page_last_reviewed TEXT        NOT NULL DEFAULT '',
    next_review_due    TEXT        NOT NULL DEFAULT '',
    markdown           TEXT        NOT NULL,
    scraped_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (domain, slug)
);
"""


async def init_db() -> None:
    """Create connection pool and apply schema. No-op if DATABASE_URL is unset."""
    global _pool
    url = os.environ.get("DATABASE_URL")
    if not url:
        return
    _pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA)


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    return _pool


async def upsert_page(
    pool: asyncpg.Pool,
    domain: str,
    slug: str,
    *,
    name: str,
    url: str,
    page_last_reviewed: str,
    next_review_due: str,
    markdown: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO scraped_pages
            (domain, slug, name, url, page_last_reviewed, next_review_due, markdown, scraped_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, now())
        ON CONFLICT (domain, slug) DO UPDATE SET
            name               = EXCLUDED.name,
            url                = EXCLUDED.url,
            page_last_reviewed = EXCLUDED.page_last_reviewed,
            next_review_due    = EXCLUDED.next_review_due,
            markdown           = EXCLUDED.markdown,
            scraped_at         = now()
        """,
        domain, slug, name, url, page_last_reviewed, next_review_due, markdown,
    )


async def list_pages(pool: asyncpg.Pool, domain: str) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT slug, name FROM scraped_pages WHERE domain = $1 ORDER BY name",
        domain,
    )


async def get_page(pool: asyncpg.Pool, domain: str, slug: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM scraped_pages WHERE domain = $1 AND slug = $2",
        domain, slug,
    )


async def delete_page(pool: asyncpg.Pool, domain: str, slug: str) -> bool:
    result = await pool.execute(
        "DELETE FROM scraped_pages WHERE domain = $1 AND slug = $2",
        domain, slug,
    )
    return result == "DELETE 1"


async def search_pages(pool: asyncpg.Pool, query: str) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT slug, name, domain
        FROM scraped_pages
        WHERE LOWER(name) LIKE $1
        ORDER BY name
        """,
        f"%{query.lower()}%",
    )
