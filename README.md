# NHS Health A-Z Scraper

A FastAPI web scraper that extracts content from the [NHS Health A-Z](https://www.nhs.uk/conditions/) website and saves it as markdown files with YAML frontmatter metadata.

Covers four domains:

- **Conditions** — `/conditions/`
- **Symptoms** — `/symptoms/`
- **Medicines** — `/medicines/`
- **Tests & Treatments** — `/treatments/`

## Quick Start

```bash
docker compose up --build -d
```

The API is available at **http://localhost:8000** and interactive docs at **http://localhost:8000/docs**.

## API Usage

### Scrape content

Start a background scrape of an entire domain:

```bash
curl -X POST http://localhost:8000/conditions/scrape
# {"task_id": "a1b2c3d4e5f6"}
```

Items that have already been scraped are **skipped by default**. To force a full re-scrape (overwrite all existing files):

```bash
curl -X POST "http://localhost:8000/conditions/scrape?force=true"
```

Scrape (or re-scrape) a single item by slug — this always overwrites the existing file:

```bash
curl -X POST http://localhost:8000/conditions/scrape/acne
```

Duplicate scrape requests are rejected with `409 Conflict` if a scrape for the same domain or slug is already running.

### Poll task progress

```bash
curl http://localhost:8000/tasks/{task_id}
# {"task_id": "...", "status": "running", "done": 42, "total": 950, ...}
```

Status values: `pending` → `running` → `completed` / `failed` / `cancelled`.

### Cancel a running task

```bash
curl -X POST http://localhost:8000/tasks/{task_id}/cancel
```

### Browse scraped content

```bash
# List all scraped items in a domain
curl http://localhost:8000/conditions/

# Get full markdown + metadata for one item
curl http://localhost:8000/conditions/acne

# Delete a cached item
curl -X DELETE http://localhost:8000/conditions/acne
```

All four domains (`/conditions/`, `/symptoms/`, `/medicines/`, `/treatments/`) expose the same endpoints.

## Scraped files

Scraped content is saved to `./data/{domain}/{slug}.md` and persisted on the host via a Docker volume mount. Example file:

```yaml
---
name: Acne
url: https://www.nhs.uk/conditions/acne/
page_last_reviewed: 03 January 2023
next_review_due: 03 January 2026
---

# Acne

## Overview
Acne is a common skin condition...

## Causes
Acne is caused by blocked hair follicles...
```

## Running Tests

```bash
docker compose run --rm app uv run pytest -v
```

## Project Structure

```
├── main.py              # FastAPI app entrypoint
├── config.py            # URLs, paths, rate limit constants
├── tasks.py             # In-memory background task store
├── scraper/
│   ├── client.py        # Rate-limited httpx client
│   ├── index.py         # A-Z index page parser
│   ├── page.py          # Detail page + sub-tab parser
│   └── markdown.py      # HTML → markdown converter
├── domains/
│   ├── models.py        # Pydantic response models
│   └── router.py        # Shared router factory (5 endpoints per domain)
├── tests/               # pytest suite (30 tests)
├── Dockerfile
└── docker-compose.yml
```
