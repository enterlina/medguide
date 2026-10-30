from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.domain import ClinicalTrialRecord, FactVerification, PublicationRecord
from app.models.evidence import (
    EvidenceAssessmentAnnotation,
    EvidenceValue,
    Missingness,
    StructuredEvidenceRecord,
)


def test_identifier_formats_are_validated() -> None:
    with pytest.raises(ValidationError):
        PublicationRecord(pmid="not-a-pmid", title="Invalid")
    with pytest.raises(ValidationError):
        ClinicalTrialRecord(
            nct_id="NCT123",
            title="Invalid",
            overall_status="UNKNOWN",
            has_results=False,
        )


def test_unknown_enrollment_remains_nullable() -> None:
    trial = ClinicalTrialRecord(
        nct_id="NCT00000001",
        title="Unknown enrollment fixture",
        overall_status="UNKNOWN",
        has_results=False,
    )
    assert trial.enrollment is None


def test_fact_verification_states_are_independent() -> None:
    verification = FactVerification(
        schema_valid=True,
        source_span_verified=True,
        human_reviewed=False,
        reviewer_note="Provenance verified; interpretation awaits review.",
    )
    assert verification.source_span_verified
    assert not verification.human_reviewed


def test_missingness_is_explicit_and_cannot_hide_a_value() -> None:
    assert EvidenceValue(state=Missingness.NOT_EXTRACTED).value is None
    with pytest.raises(ValidationError):
        EvidenceValue(state=Missingness.REPORTED)
    with pytest.raises(ValidationError):
        EvidenceValue(state=Missingness.NOT_REPORTED, value="hidden")


def test_unreviewed_record_cannot_be_admitted() -> None:
    value = {"state": "not_extracted"}
    payload = {
        "evidence_record_id": "pubmed:123",
        "source": "pubmed",
        "source_document_id": "pubmed:123",
        "pmid": "123",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/123/",
        "ingredient_ids": ["creatine-monohydrate"],
        "research_question": value,
        "study_type": value,
        "pico": {
            "population": value,
            "intervention": value,
            "comparator": value,
            "outcomes": value,
        },
        "sample_size": value,
        "dose": value,
        "frequency": value,
        "duration": value,
        "results": value,
        "adverse_events": value,
        "limitations": value,
        "funding": value,
        "sponsor": value,
        "manufacturer_involvement": {
            "company_funded": value,
            "product_supplied": value,
            "manufacturer_employees_involved": value,
            "author_financial_relationships": value,
            "independence_confirmed": value,
        },
        "risk_of_bias": value,
        "freshness": {
            "last_checked_at": "2026-10-27T12:00:00Z",
            "evidence_version": "test-v1",
        },
        "verification": {
            "schema_valid": True,
            "source_span_verified": False,
            "human_reviewed": False,
        },
        "admitted_to_evidence": True,
    }
    with pytest.raises(ValidationError, match="evidence admission requires"):
        StructuredEvidenceRecord.model_validate(payload)


def test_topic_relevance_is_separate_from_applicability() -> None:
    annotation = EvidenceAssessmentAnnotation(
        query_id="q1",
        source_document_id="pubmed:123",
        topic_relevance=2,
        ingredient_form="different",
        population="different",
        dose="not_reported",
        outcome="direct",
        human_reviewed=True,
        reviewer="reviewer-1",
    )
    assert annotation.topic_relevance == 2
    assert annotation.ingredient_form == "different"


def test_unreviewed_annotation_does_not_invent_topic_gold() -> None:
    annotation = EvidenceAssessmentAnnotation(query_id="q1", source_document_id="pubmed:123")
    assert annotation.topic_relevance is None
    assert annotation.human_reviewed is False
