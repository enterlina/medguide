from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
from app.interactions.catalog import IngredientCatalog
from app.interactions.extractor import ConservativeRuleExtractor
from app.interactions.models import Ingredient, LabelDocument
from app.interactions.repository import InteractionRepository


def build_repository(path: Path) -> tuple[InteractionRepository, str]:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Drug alpha may increase exposure to drug beta."
    label = LabelDocument(
        label_id="fixture:review-api:1",
        source="fixture",
        source_url="https://example.invalid/review-api/1",
        version="1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    rule = ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")[0]
    repository = InteractionRepository(path)
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(label, [rule])
    return repository, rule.interaction_id


def configure_reviewers(monkeypatch) -> dict[str, str]:
    monkeypatch.delenv("MEDGUIDE_REVIEW_DEV_BYPASS", raising=False)
    tokens = {
        "source-token": {
            "reviewer_id": "source-001",
            "display_name": "Source Reviewer",
            "roles": ["source_reviewer"],
        },
        "clinical-token": {
            "reviewer_id": "clinical-001",
            "display_name": "Clinical Reviewer",
            "roles": ["clinical_reviewer"],
        },
    }
    monkeypatch.setenv("MEDGUIDE_REVIEWER_TOKENS", json.dumps(tokens))
    return {
        "source": "Bearer source-token",
        "clinical": "Bearer clinical-token",
    }


def test_local_review_bypass_is_development_only(monkeypatch) -> None:
    monkeypatch.setenv("MEDGUIDE_REVIEW_DEV_BYPASS", "true")
    monkeypatch.setenv("MEDGUIDE_ENV", "development")
    client = TestClient(main_module.app)

    session = client.get("/api/interactions/review/session")
    assert session.status_code == 200
    assert session.json() == {
        "reviewer_id": "local-reviewer",
        "display_name": "Local Development Reviewer",
        "roles": ["admin"],
    }

    monkeypatch.setenv("MEDGUIDE_ENV", "production")
    assert client.get("/api/interactions/review/session").status_code == 401


def test_review_dashboard_queue_detail_transitions_conflict_and_history(
    tmp_path: Path, monkeypatch
) -> None:
    repository, rule_id = build_repository(tmp_path / "review-api.sqlite3")
    monkeypatch.setattr(main_module, "interaction_repository", repository)
    auth = configure_reviewers(monkeypatch)
    client = TestClient(main_module.app)

    assert client.get("/api/interactions/review").status_code == 401
    source_headers = {"Authorization": auth["source"]}
    clinical_headers = {"Authorization": auth["clinical"]}

    summary = client.get("/api/interactions/review/summary", headers=source_headers)
    assert summary.status_code == 200
    assert summary.json()["extracted"] == 1
    queue = client.get(
        "/api/interactions/review?status=extracted&interaction_type=drug_drug",
        headers=source_headers,
    )
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    detail = client.get(f"/api/interactions/review/{rule_id}", headers=source_headers)
    assert detail.status_code == 200
    assert detail.json()["source_match"] is True
    assert detail.json()["document_version"] == "1"

    missing_comment = client.post(
        f"/api/interactions/review/{rule_id}",
        headers=source_headers,
        json={"target_status": "source_span_verified", "expected_status": "extracted", "comment": ""},
    )
    assert missing_comment.status_code == 422
    forbidden = client.post(
        f"/api/interactions/review/{rule_id}",
        headers=source_headers,
        json={
            "target_status": "human_reviewed",
            "expected_status": "extracted",
            "comment": "Attempted clinical approval by source reviewer.",
        },
    )
    assert forbidden.status_code == 403

    verified = client.post(
        f"/api/interactions/review/{rule_id}",
        headers=source_headers,
        json={
            "target_status": "source_span_verified",
            "expected_status": "extracted",
            "comment": "Exact source passage confirmed.",
        },
    )
    assert verified.status_code == 200
    assert verified.json()["reviewer"] == "source-001"
    conflict = client.post(
        f"/api/interactions/review/{rule_id}",
        headers=source_headers,
        json={
            "target_status": "rejected",
            "expected_status": "extracted",
            "comment": "Stale review attempt.",
        },
    )
    assert conflict.status_code == 409

    approved = client.post(
        f"/api/interactions/review/{rule_id}",
        headers=clinical_headers,
        json={
            "target_status": "human_reviewed",
            "expected_status": "source_span_verified",
            "comment": "Interaction interpretation and applicability reviewed.",
        },
    )
    assert approved.status_code == 200
    history = client.get(
        f"/api/interactions/review/{rule_id}/history", headers=clinical_headers
    )
    assert history.status_code == 200
    assert [event["new_status"] for event in history.json()] == [
        "source_span_verified",
        "human_reviewed",
    ]


def test_source_reviewer_can_reject_extracted_rule(tmp_path: Path, monkeypatch) -> None:
    repository, rule_id = build_repository(tmp_path / "review-reject.sqlite3")
    monkeypatch.setattr(main_module, "interaction_repository", repository)
    auth = configure_reviewers(monkeypatch)
    client = TestClient(main_module.app)
    note = client.post(
        f"/api/interactions/review/{rule_id}/notes",
        headers={"Authorization": auth["source"]},
        json={
            "kind": "correction",
            "expected_status": "extracted",
            "comment": "Please correct the extracted recommendation before source verification.",
        },
    )
    assert note.status_code == 200
    assert note.json()["previous_status"] == note.json()["new_status"] == "extracted"
    response = client.post(
        f"/api/interactions/review/{rule_id}",
        headers={"Authorization": auth["source"]},
        json={
            "target_status": "rejected",
            "expected_status": "extracted",
            "comment": "Source passage does not support the extracted interpretation.",
        },
    )
    assert response.status_code == 200
    assert response.json()["new_status"] == "rejected"
    history = client.get(
        f"/api/interactions/review/{rule_id}/history",
        headers={"Authorization": auth["source"]},
    ).json()
    assert history[0]["note"].startswith("REQUEST_CORRECTION:")
