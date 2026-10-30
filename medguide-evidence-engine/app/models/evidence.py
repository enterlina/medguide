from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models.domain import FactVerification, SourceName


class Missingness(StrEnum):
    REPORTED = "reported"
    NOT_REPORTED = "not_reported"
    NOT_EXTRACTED = "not_extracted"
    NOT_APPLICABLE = "not_applicable"


class PublicationIntegrity(StrEnum):
    NO_NOTICE_FOUND = "no_integrity_notice_found"
    CORRECTED_OR_ERRATUM = "corrected_or_erratum"
    RETRACTED = "retracted"
    RETRACTION_NOTICE = "retraction_notice"


class EvidenceValue(BaseModel):
    """A value whose absence has an explicit, non-interchangeable meaning."""

    model_config = ConfigDict(extra="forbid")

    state: Missingness
    value: Any | None = None
    unit: str | None = None
    source_quote: str | None = None

    @model_validator(mode="after")
    def state_matches_value(self) -> EvidenceValue:
        if self.state == Missingness.REPORTED and self.value is None:
            raise ValueError("reported values require a value")
        if self.state != Missingness.REPORTED and self.value is not None:
            raise ValueError("non-reported states cannot carry a value")
        return self


class Ingredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    canonical_name: str
    synonyms: list[str] = Field(default_factory=list)
    scientific_terms: list[str] = Field(default_factory=list)
    forms: list[str] = Field(default_factory=list)


class ProductIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: str
    form: EvidenceValue
    amount: EvidenceValue


class SupplementProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    display_name: str
    market: str | None = None
    manufacturer: EvidenceValue
    ingredients: list[ProductIngredient]


class SupplementCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_version: str
    created_at: datetime
    ingredients: list[Ingredient]
    products: list[SupplementProduct] = Field(default_factory=list)


class PICO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    population: EvidenceValue
    intervention: EvidenceValue
    comparator: EvidenceValue
    outcomes: EvidenceValue


class ManufacturerInvolvement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_funded: EvidenceValue
    product_supplied: EvidenceValue
    manufacturer_employees_involved: EvidenceValue
    author_financial_relationships: EvidenceValue
    independence_confirmed: EvidenceValue


class FreshnessMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    published_at: datetime | None = None
    indexed_at: datetime | None = None
    source_updated_at: datetime | None = None
    last_checked_at: datetime
    evidence_version: str


class StructuredEvidenceRecord(BaseModel):
    """Extracted evidence. Discovery results must not be instantiated as admitted records."""

    model_config = ConfigDict(extra="forbid")

    evidence_record_id: str
    source: SourceName
    source_document_id: str
    pmid: str | None = Field(default=None, pattern=r"^\d{1,9}$")
    doi: str | None = None
    nct_id: str | None = Field(default=None, pattern=r"^NCT\d{8}$")
    source_url: HttpUrl
    publication_integrity: PublicationIntegrity = PublicationIntegrity.NO_NOTICE_FOUND
    publication_events: list[dict[str, str]] = Field(default_factory=list)
    ingredient_ids: list[str]
    product_ids: list[str] = Field(default_factory=list)
    research_question: EvidenceValue
    study_type: EvidenceValue
    pico: PICO
    sample_size: EvidenceValue
    dose: EvidenceValue
    frequency: EvidenceValue
    duration: EvidenceValue
    results: EvidenceValue
    adverse_events: EvidenceValue
    limitations: EvidenceValue
    funding: EvidenceValue
    sponsor: EvidenceValue
    manufacturer_involvement: ManufacturerInvolvement
    risk_of_bias: EvidenceValue
    freshness: FreshnessMetadata
    verification: FactVerification
    admitted_to_evidence: bool = False

    @model_validator(mode="after")
    def admission_requires_review(self) -> StructuredEvidenceRecord:
        if (
            self.admitted_to_evidence
            and self.publication_integrity == PublicationIntegrity.RETRACTED
        ):
            raise ValueError("retracted publications cannot be admitted to evidence")
        if self.admitted_to_evidence and not (
            self.verification.schema_valid
            and self.verification.source_span_verified
            and self.verification.human_reviewed
        ):
            raise ValueError("evidence admission requires schema, source-span, and human review")
        return self


class ScientificSection(StrEnum):
    ABSTRACT = "abstract"
    METHODS = "methods"
    PARTICIPANTS = "participants"
    INTERVENTION = "intervention"
    RESULTS = "results"
    ADVERSE_EVENTS = "adverse_events"
    LIMITATIONS = "limitations"
    FUNDING_CONFLICTS = "funding_conflicts"


class EvidenceChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_record_id: str
    section: ScientificSection
    ingredient_ids: list[str]
    outcome_terms: list[str] = Field(default_factory=list)
    population_terms: list[str] = Field(default_factory=list)
    processing_fingerprint: str


class ApplicabilityMatch(StrEnum):
    EXACT = "exact"
    RELATED = "related"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


class PopulationMatch(StrEnum):
    MATCH = "match"
    PARTIAL = "partial"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


class DoseMatch(StrEnum):
    MATCH = "match"
    DIFFERENT = "different"
    NOT_REPORTED = "not_reported"


class OutcomeMatch(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    NOT_MEASURED = "not_measured"


class EvidenceAssessmentAnnotation(BaseModel):
    """Human annotation interface; applicability never acts as a retrieval exclusion rule."""

    model_config = ConfigDict(extra="forbid")

    query_id: str
    source_document_id: str
    topic_relevance: int | None = Field(default=None, ge=0, le=3)
    ingredient_form: ApplicabilityMatch = ApplicabilityMatch.UNKNOWN
    population: PopulationMatch = PopulationMatch.UNKNOWN
    dose: DoseMatch = DoseMatch.NOT_REPORTED
    outcome: OutcomeMatch = OutcomeMatch.NOT_MEASURED
    study_design: str | None = None
    study_quality: Literal["high", "moderate", "low", "unclear"] = "unclear"
    evidence_direction: Literal["positive", "negative", "mixed", "inconclusive"] = "inconclusive"
    citation_support: Literal["supported", "contradicted", "unsupported", "unclear"] = "unclear"
    human_reviewed: bool = False
    reviewer: str | None = None

    @model_validator(mode="after")
    def reviewed_annotations_require_reviewer(self) -> EvidenceAssessmentAnnotation:
        if self.human_reviewed and (self.topic_relevance is None or not self.reviewer):
            raise ValueError("human-reviewed topic relevance requires a score and reviewer")
        return self
