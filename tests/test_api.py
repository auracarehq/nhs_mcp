from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(tmp_data_dir):
    with TestClient(app) as c:
        yield c


def _write_md(data_dir: Path, slug: str, name: str = "Test") -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / f"{slug}.md").write_text(
        f"---\nname: {name}\nurl: https://example.com/{slug}/\n"
        f"page_last_reviewed: '01 Jan 2024'\nnext_review_due: '01 Jan 2027'\n---\n# {name}\nContent here.\n"
    )


def test_list_empty(client):
    resp = client.get("/conditions/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_with_items(client, tmp_data_dir):
    _write_md(tmp_data_dir / "conditions", "acne", "Acne")
    _write_md(tmp_data_dir / "conditions", "asthma", "Asthma")
    resp = client.get("/conditions/")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    slugs = {i["slug"] for i in items}
    assert slugs == {"acne", "asthma"}


def test_get_item(client, tmp_data_dir):
    _write_md(tmp_data_dir / "conditions", "acne", "Acne")
    resp = client.get("/conditions/acne")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "acne"
    assert data["name"] == "Acne"
    assert "# Acne" in data["markdown"]


def test_get_item_not_found(client):
    resp = client.get("/conditions/nonexistent")
    assert resp.status_code == 404


def test_delete_item(client, tmp_data_dir):
    _write_md(tmp_data_dir / "conditions", "acne", "Acne")
    resp = client.delete("/conditions/acne")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "acne"}
    assert not (tmp_data_dir / "conditions" / "acne.md").exists()


def test_delete_not_found(client):
    resp = client.delete("/conditions/nonexistent")
    assert resp.status_code == 404


def test_scrape_single_returns_task_id(client):
    with patch("domains.router.scrape_page", new_callable=AsyncMock) as mock_scrape:
        from scraper.page import PageData, Section
        mock_scrape.return_value = PageData(
            name="Acne", url="https://www.nhs.uk/conditions/acne/",
            sections=[Section(title="", html="<p>Content</p>")],
        )
        resp = client.post("/conditions/scrape/acne")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data


def test_scrape_all_returns_task_id(client):
    with patch("domains.router.scrape_index", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = []
        resp = client.post("/conditions/scrape")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data


def test_task_status(client):
    from tasks import create_task
    task = create_task()
    resp = client.get(f"/tasks/{task.task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_task_not_found(client):
    resp = client.get("/tasks/nonexistent")
    assert resp.status_code == 404


def test_symptoms_router_exists(client):
    resp = client.get("/symptoms/")
    assert resp.status_code == 200


def test_medicines_router_exists(client):
    resp = client.get("/medicines/")
    assert resp.status_code == 200


def test_treatments_router_exists(client):
    resp = client.get("/treatments/")
    assert resp.status_code == 200


def test_search_empty_query(client):
    resp = client.get("/search")
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_returns_matching(client, tmp_data_dir):
    _write_md(tmp_data_dir / "conditions", "acne", "Acne")
    _write_md(tmp_data_dir / "conditions", "asthma", "Asthma")
    resp = client.get("/search?q=acne")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["slug"] == "acne"
    assert results[0]["name"] == "Acne"
    assert results[0]["domain"] == "conditions"


def test_search_cross_domain(client, tmp_data_dir):
    _write_md(tmp_data_dir / "conditions", "acne", "Acne")
    _write_md(tmp_data_dir / "medicines", "acne-gel", "Acne Gel")
    resp = client.get("/search?q=acne")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    domains = {r["domain"] for r in results}
    assert domains == {"conditions", "medicines"}
