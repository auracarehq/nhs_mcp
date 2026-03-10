# CLAUDE.md

Python + Docker codebase.

## Run & Test

```bash
docker compose up --build                          # API + Postgres
docker compose --profile tools run --rm test       # all tests (style + unit)
```

## Architecture

- `main.py`: FastAPI app, lifespan, top-level routes (Swagger at `/docs`)
- `config.py`: scraper rate-limiting config
- `db.py`: SQLAlchemy async ORM (asyncpg driver), models and CRUD
- `tasks.py`: in-memory task store for background scrapes
- `domains/models.py`: shared response models (TaskResponse, SearchResult)
- `domains/nhs/config.py`: NHS-specific config (base URL, domain registry)
- `domains/nhs/models.py`: NHS response models (ItemSummary, ItemContent)
- `domains/nhs/service.py`: shared scrape orchestration
- `domains/nhs/{conditions,symptoms,medicines,treatments}/router.py`: per-domain routers
- `scraper/`: HTTP client, index parser, page parser, markdown converter
- `tests/`: pytest unit tests
- `tests/style/`: structural style tests (complexity, architecture, security, dead code, docs)

## Conventions

- Keep `scraper/` independent — no imports from `domains`, `tasks`, or `main`.
- Domain models stay dependency-free (no imports from `scraper`, `db`, `tasks`, `main`).
- Postgres is the system of record — no filesystem storage.
- Style tests enforce limits automatically.
