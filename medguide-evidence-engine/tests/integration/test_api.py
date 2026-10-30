from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_ready_do_not_leak_configuration() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready").json()
    assert ready["status"] == "ready"
    assert ready["chunks"] <= 500
    assert "key" not in str(ready).lower()


def test_search_returns_source_trace_and_distinct_scores() -> None:
    response = client.post(
        "/api/v1/search",
        json={"query": "magnesium gluconate posted results", "top_k": 3},
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["source_uri"].startswith("https://")
    assert result["source_document_id"].startswith(("pubmed:", "pmc:", "trial:"))
    assert set(result["scores"]) == {"dense", "bm25", "rrf", "rerank"}


def test_unsupported_scope_abstains_without_citations() -> None:
    response = client.post(
        "/api/v1/ask", json={"question": "Does magnesium citrate cure insomnia in children?"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["citations"] == []


def test_invalid_filter_returns_no_results() -> None:
    response = client.post(
        "/api/v1/search",
        json={"query": "magnesium sleep", "filters": {"form": "magnesium citrate"}},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NO_RESULTS"


def test_admin_endpoints_are_closed_when_auth_is_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("MEDGUIDE_ADMIN_TOKEN", raising=False)
    assert client.post("/api/v1/ingestion/runs").status_code == 503
    assert client.post("/api/v1/index/build").status_code == 503

