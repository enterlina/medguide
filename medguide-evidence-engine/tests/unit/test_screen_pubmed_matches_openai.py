from scripts.screen_pubmed_matches_openai import ModelAssessment, validate_and_finalize


def assessment(**overrides):
    values = {
        "entity_match": "exact",
        "study_role": "primary_intervention",
        "outcome_match": "direct",
        "effect_attribution": "isolated",
        "proposed_decision": "include",
        "confidence": "high",
        "evidence_quotes": ["Magnesium improved sleep quality."],
        "reason": "The intervention and outcome are directly evaluated.",
    }
    values.update(overrides)
    return ModelAssessment(**values)


def test_direct_high_confidence_match_is_included():
    result = validate_and_finalize(
        assessment(), "METHODS. Magnesium improved sleep quality. RESULTS."
    )
    assert result["decision"] == "include"
    assert result["validation_errors"] == []


def test_rescue_medication_is_excluded():
    result = validate_and_finalize(
        assessment(
            study_role="rescue_medication",
            proposed_decision="include",
            evidence_quotes=["Patients received rescue paracetamol."],
        ),
        "Patients received rescue paracetamol.",
    )
    assert result["decision"] == "exclude"


def test_non_verbatim_quote_forces_human_review():
    result = validate_and_finalize(assessment(), "No matching sentence is present.")
    assert result["decision"] == "needs_review"
    assert result["confidence"] == "low"
    assert result["evidence_quotes"] == []
    assert result["validation_errors"] == ["one_or_more_quotes_not_found_verbatim"]


def test_shared_component_in_both_arms_is_only_indirect_evidence():
    result = validate_and_finalize(
        assessment(effect_attribution="shared_both_arms"),
        "Magnesium improved sleep quality.",
    )
    assert result["decision"] == "include_as_indirect"
