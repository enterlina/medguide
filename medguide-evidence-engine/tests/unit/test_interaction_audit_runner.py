from __future__ import annotations

import json
from pathlib import Path

from scripts.run_interaction_audit import grade, normalized_response


ROOT = Path(__file__).parents[2]


def test_fixture_has_all_unique_cases() -> None:
    fixture = json.loads((ROOT / "tests/fixtures/interaction_gold_v1.json").read_text())
    ids = [case["id"] for case in fixture["cases"]]
    assert len(ids) == 56
    assert len(ids) == len(set(ids))
    assert ids[0] == "MG001"
    assert ids[-1] == "MG056"
    assert len(fixture["resolver_inventory"]) == 100


def test_normalizer_deduplicates_same_rule_across_buckets() -> None:
    rule = {
        "interaction_id": "rule-1",
        "interaction_type": "drug_drug",
        "status": "CAUTION",
        "effect": "May increase bleeding risk.",
        "recommended_action": "Monitor for bleeding.",
        "validation_status": "source_span_verified",
        "source_passage": {"source_url": "https://example.test/label"},
    }
    normalized = normalized_response(
        {
            "medications": [],
            "interactions": [],
            "preliminary_findings": [rule],
            "label_mentions": [rule],
        }
    )
    assert len(normalized["findings"]) == 1


def test_review_required_match_is_not_automatically_passed() -> None:
    case = {
        "interaction_type": "drug_drug",
        "must_detect": True,
        "expected_effect": "Increased bleeding risk",
        "must_include_qualifiers": [],
        "reference_status": "review_required",
        "context": {"raw": "warfarin + ibuprofen"},
    }
    normalized = {
        "resolved": [{"input_name": "warfarin", "ingredient_ids": ["x"]}],
        "findings": [{"effect": "Increased bleeding risk", "action": "Monitor", "source_url": "https://example.test"}],
        "duplicates": [],
    }
    status, _ = grade(case, normalized)
    assert status == "NEEDS_HUMAN_REVIEW"
