"""Database layer using SQLAlchemy async with asyncpg."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import Boolean, String, Text, select, delete as sa_delete, func
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


class SnomedConcept(Base):
    """A locally cached SNOMED CT concept fetched from the Snowstorm API."""

    __tablename__ = "snomed_concepts"

    concept_id: Mapped[str] = mapped_column(String, primary_key=True)
    preferred_term: Mapped[str] = mapped_column(String, nullable=False)
    fsn: Mapped[str] = mapped_column(String, nullable=False)
    hierarchy: Mapped[str] = mapped_column(String, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc),
    )


class Icd11Concept(Base):
    """A locally cached ICD-11 concept fetched from the WHO ICD API."""

    __tablename__ = "icd11_concepts"

    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    icd_code: Mapped[str] = mapped_column(String, nullable=False, default="")
    title: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc),
    )


class DmdProduct(Base):
    """A locally cached dm+d product fetched via Snowstorm ECL + NHS Terminology Server."""

    __tablename__ = "dmd_products"

    dmd_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    concept_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    bnf_code: Mapped[str] = mapped_column(String, nullable=False, default="")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
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
    # asyncpg uses ssl=True, not sslmode=require — strip and translate
    connect_args: dict = {}
    if "sslmode=" in raw_url:
        parsed = urlparse(raw_url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        sslmode = query.pop("sslmode", [None])[0]
        if sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = True
        raw_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in query.items()})))
    _engine = create_async_engine(raw_url, pool_size=5, max_overflow=0, connect_args=connect_args)
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


async def cache_snomed_concept(
    concept_id: str,
    preferred_term: str,
    fsn: str,
    hierarchy: str,
    active: bool,
    raw_json: str,
) -> None:
    """Insert or update a cached SNOMED CT concept."""
    async with get_session() as session:
        existing = await session.get(SnomedConcept, concept_id)
        if existing:
            existing.preferred_term = preferred_term
            existing.fsn = fsn
            existing.hierarchy = hierarchy
            existing.active = active
            existing.raw_json = raw_json
            existing.cached_at = datetime.now(timezone.utc)
        else:
            session.add(SnomedConcept(
                concept_id=concept_id,
                preferred_term=preferred_term,
                fsn=fsn,
                hierarchy=hierarchy,
                active=active,
                raw_json=raw_json,
            ))
        await session.commit()


def _snomed_row_to_dict(r: SnomedConcept) -> dict:
    """Convert a SnomedConcept ORM row to a plain dict."""
    return {"concept_id": r.concept_id, "preferred_term": r.preferred_term, "fsn": r.fsn,
            "hierarchy": r.hierarchy, "active": r.active, "raw_json": r.raw_json, "cached_at": r.cached_at}


async def get_snomed_concept(concept_id: str) -> dict | None:
    """Fetch a single cached SNOMED CT concept by ID."""
    async with get_session() as session:
        row = await session.get(SnomedConcept, concept_id)
        return _snomed_row_to_dict(row) if row else None


async def list_snomed_concepts() -> list[dict]:
    """Return all cached SNOMED CT concepts, ordered by preferred term."""
    async with get_session() as session:
        result = await session.execute(select(SnomedConcept).order_by(SnomedConcept.preferred_term))
        return [_snomed_row_to_dict(r) for r in result.scalars()]


async def delete_snomed_concept(concept_id: str) -> bool:
    """Delete a cached SNOMED CT concept. Returns True if a row was removed."""
    async with get_session() as session:
        result = await session.execute(
            sa_delete(SnomedConcept).where(SnomedConcept.concept_id == concept_id)
        )
        await session.commit()
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# ICD-11 CRUD
# ---------------------------------------------------------------------------

async def cache_icd11_concept(
    entity_id: str,
    icd_code: str,
    title: str,
    definition: str,
    raw_json: str,
) -> None:
    """Insert or update a cached ICD-11 concept."""
    async with get_session() as session:
        existing = await session.get(Icd11Concept, entity_id)
        if existing:
            existing.icd_code = icd_code
            existing.title = title
            existing.definition = definition
            existing.raw_json = raw_json
            existing.cached_at = datetime.now(timezone.utc)
        else:
            session.add(Icd11Concept(
                entity_id=entity_id, icd_code=icd_code, title=title,
                definition=definition, raw_json=raw_json,
            ))
        await session.commit()


async def get_icd11_concept(entity_id: str) -> dict | None:
    """Fetch a single cached ICD-11 concept by entity ID."""
    async with get_session() as session:
        row = await session.get(Icd11Concept, entity_id)
        if row is None:
            return None
        return {"entity_id": row.entity_id, "icd_code": row.icd_code, "title": row.title,
                "definition": row.definition, "raw_json": row.raw_json, "cached_at": row.cached_at}


def _icd_row_to_dict(r: Icd11Concept) -> dict:
    """Convert an Icd11Concept ORM row to a plain dict."""
    return {"entity_id": r.entity_id, "icd_code": r.icd_code, "title": r.title,
            "definition": r.definition, "raw_json": r.raw_json, "cached_at": r.cached_at}


async def list_icd11_concepts() -> list[dict]:
    """Return all cached ICD-11 concepts, ordered by title."""
    async with get_session() as session:
        result = await session.execute(select(Icd11Concept).order_by(Icd11Concept.title))
        return [_icd_row_to_dict(r) for r in result.scalars()]


async def delete_icd11_concept(entity_id: str) -> bool:
    """Delete a cached ICD-11 concept. Returns True if a row was removed."""
    async with get_session() as session:
        result = await session.execute(
            sa_delete(Icd11Concept).where(Icd11Concept.entity_id == entity_id)
        )
        await session.commit()
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# dm+d CRUD
# ---------------------------------------------------------------------------

async def cache_dmd_product(
    dmd_id: str,
    name: str,
    concept_type: str,
    bnf_code: str,
    raw_json: str,
) -> None:
    """Insert or update a cached dm+d product."""
    async with get_session() as session:
        existing = await session.get(DmdProduct, dmd_id)
        if existing:
            existing.name = name
            existing.concept_type = concept_type
            existing.bnf_code = bnf_code
            existing.raw_json = raw_json
            existing.cached_at = datetime.now(timezone.utc)
        else:
            session.add(DmdProduct(
                dmd_id=dmd_id, name=name, concept_type=concept_type,
                bnf_code=bnf_code, raw_json=raw_json,
            ))
        await session.commit()


async def get_dmd_product(dmd_id: str) -> dict | None:
    """Fetch a single cached dm+d product by ID."""
    async with get_session() as session:
        row = await session.get(DmdProduct, dmd_id)
        if row is None:
            return None
        return {"dmd_id": row.dmd_id, "name": row.name, "concept_type": row.concept_type,
                "bnf_code": row.bnf_code, "raw_json": row.raw_json, "cached_at": row.cached_at}


def _dmd_row_to_dict(r: DmdProduct) -> dict:
    """Convert a DmdProduct ORM row to a plain dict."""
    return {"dmd_id": r.dmd_id, "name": r.name, "concept_type": r.concept_type,
            "bnf_code": r.bnf_code, "raw_json": r.raw_json, "cached_at": r.cached_at}


async def list_dmd_products() -> list[dict]:
    """Return all cached dm+d products, ordered by name."""
    async with get_session() as session:
        result = await session.execute(select(DmdProduct).order_by(DmdProduct.name))
        return [_dmd_row_to_dict(r) for r in result.scalars()]


async def delete_dmd_product(dmd_id: str) -> bool:
    """Delete a cached dm+d product. Returns True if a row was removed."""
    async with get_session() as session:
        result = await session.execute(
            sa_delete(DmdProduct).where(DmdProduct.dmd_id == dmd_id)
        )
        await session.commit()
        return result.rowcount > 0
