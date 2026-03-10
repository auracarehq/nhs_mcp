"""Database layer using SQLAlchemy async with asyncpg."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import String, Text, select, delete as sa_delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_DATABASE_URL_DEFAULT = "postgresql+asyncpg://nhs:nhs@db:5432/nhs_scraper"

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class ScrapedPage(Base):
    """A scraped NHS page stored in PostgreSQL."""

    __tablename__ = "scraped_pages"

    domain: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False, default="")
    page_last_reviewed: Mapped[str] = mapped_column(String, nullable=False, default="")
    next_review_due: Mapped[str] = mapped_column(String, nullable=False, default="")
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc),
    )


async def init_db() -> None:
    """Create the async engine, session factory, and tables."""
    global _engine, _session_factory
    raw_url = os.environ.get("DATABASE_URL", _DATABASE_URL_DEFAULT)
    # Normalise postgres:// to postgresql+asyncpg://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    _engine = create_async_engine(raw_url, pool_size=5, max_overflow=0)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine and connection pool."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_session() -> AsyncSession:
    """Return a new async session."""
    assert _session_factory is not None, "Database not initialised — call init_db() first"
    return _session_factory()


# Keep get_pool as an alias so existing call sites don't break during transition.
get_pool = get_session


async def upsert_page(  # noqa: PLR0913
    _session_or_pool,
    domain: str,
    slug: str,
    *,
    name: str,
    url: str,
    page_last_reviewed: str,
    next_review_due: str,
    markdown: str,
) -> None:
    """Insert or update a scraped page row."""
    async with get_session() as session:
        existing = await session.get(ScrapedPage, (domain, slug))
        if existing:
            existing.name = name
            existing.url = url
            existing.page_last_reviewed = page_last_reviewed
            existing.next_review_due = next_review_due
            existing.markdown = markdown
            existing.scraped_at = datetime.now(timezone.utc)
        else:
            session.add(ScrapedPage(
                domain=domain, slug=slug, name=name, url=url,
                page_last_reviewed=page_last_reviewed,
                next_review_due=next_review_due, markdown=markdown,
            ))
        await session.commit()


async def list_pages(_session_or_pool, domain: str) -> list[dict]:
    """Return all pages for a domain, ordered by name."""
    async with get_session() as session:
        result = await session.execute(
            select(ScrapedPage.slug, ScrapedPage.name)
            .where(ScrapedPage.domain == domain)
            .order_by(ScrapedPage.name)
        )
        return [{"slug": r.slug, "name": r.name} for r in result.all()]


async def get_page(_session_or_pool, domain: str, slug: str) -> dict | None:
    """Fetch a single page by domain and slug."""
    async with get_session() as session:
        page = await session.get(ScrapedPage, (domain, slug))
        if page is None:
            return None
        return {
            "slug": page.slug, "name": page.name, "url": page.url,
            "domain": page.domain,
            "page_last_reviewed": page.page_last_reviewed,
            "next_review_due": page.next_review_due,
            "markdown": page.markdown,
            "scraped_at": page.scraped_at,
        }


async def delete_page(_session_or_pool, domain: str, slug: str) -> bool:
    """Delete a page and return True if a row was removed."""
    async with get_session() as session:
        result = await session.execute(
            sa_delete(ScrapedPage)
            .where(ScrapedPage.domain == domain, ScrapedPage.slug == slug)
        )
        await session.commit()
        return result.rowcount > 0


async def search_pages(_session_or_pool, query: str) -> list[dict]:
    """Search pages by name (case-insensitive substring match)."""
    async with get_session() as session:
        result = await session.execute(
            select(ScrapedPage.slug, ScrapedPage.name, ScrapedPage.domain)
            .where(func.lower(ScrapedPage.name).contains(query.lower()))
            .order_by(ScrapedPage.name)
        )
        return [{"slug": r.slug, "name": r.name, "domain": r.domain} for r in result.all()]
