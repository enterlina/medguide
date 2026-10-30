from __future__ import annotations

from enum import StrEnum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class InteractionType(StrEnum):
    DRUG_DRUG = "drug_drug"
    DRUG_SUPPLEMENT = "drug_supplement"
    DRUG_FOOD = "drug_food"
    DRUG_BEVERAGE = "drug_beverage"
    TIMING = "timing_separation"
    CONTRAINDICATION = "contraindication"
    POPULATION_WARNING = "population_specific_warning"


class InteractionStatus(StrEnum):
    CONTRAINDICATED = "CONTRAINDICATED"
    AVOID_COMBINATION = "AVOID_COMBINATION"
    CAUTION = "CAUTION"
    MONITORING_REQUIRED = "MONITORING_REQUIRED"
    SEPARATE_IN_TIME = "SEPARATE_IN_TIME"
    NO_INTERACTION_DOCUMENTED = "NO_INTERACTION_DOCUMENTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ValidationStatus(StrEnum):
    EXTRACTED = "extracted"
    SOURCE_SPAN_VERIFIED = "source_span_verified"
    HUMAN_REVIEWED = "human_reviewed"
    REJECTED = "rejected"


class TimingDirection(StrEnum):
    A_BEFORE_B = "A_BEFORE_B"
    A_AFTER_B = "A_AFTER_B"
    EITHER_DIRECTION = "EITHER_DIRECTION"
    UNSPECIFIED = "UNSPECIFIED"


class Ingredient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredient_id: str
    canonical_name: str
    rxcui: str | None = None
    aliases: list[str] = Field(default_factory=list)
    ingredient_kind: str = "drug"


class MedicationProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")
    medication_id: str
    brand_name: str | None = None
    generic_name: str
    active_ingredient_ids: list[str]
    rxcui: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    route: str | None = None


class LabelDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_id: str
    source: str
    source_url: HttpUrl
    set_id: str | None = None
    version: str | None = None
    effective_time: str | None = None
    product_name: str | None = None
    rxcui: str | None = None
    ingredient_ids: list[str] = Field(default_factory=list)
    sections: dict[str, list[str]] = Field(default_factory=dict)
    content_hash: str


class SourcePassage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    label_id: str
    source_url: HttpUrl
    readable_url: HttpUrl | None = None
    section: str
    text: str = Field(min_length=1)


class TimingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum_interval_minutes: int | None = Field(default=None, ge=0)
    direction: TimingDirection = TimingDirection.UNSPECIFIED
    exact_interval_stated: bool = False


class InteractionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interaction_id: str
    subject_id: str
    object_id: str
    interaction_type: InteractionType
    status: InteractionStatus
    severity: str | None = None
    effect: str
    recommended_action: str
    timing_rule: TimingRule | None = None
    conditions: list[str] = Field(default_factory=list)
    applicable_routes: list[str] = Field(default_factory=list)
    applicable_dosage_forms: list[str] = Field(default_factory=list)
    applicable_strengths: list[str] = Field(default_factory=list)
    source_passage: SourcePassage
    validation_status: ValidationStatus = ValidationStatus.EXTRACTED

    @model_validator(mode="after")
    def validate_rule(self) -> "InteractionRule":
        if self.subject_id == self.object_id:
            raise ValueError("interaction endpoints must be distinct")
        if self.status == InteractionStatus.SEPARATE_IN_TIME and self.timing_rule is None:
            raise ValueError("SEPARATE_IN_TIME requires a timing rule")
        return self


class MedicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    strength: str | None = Field(default=None, max_length=100)
    dosage_form: str | None = Field(default=None, max_length=100)
    route: str | None = Field(default=None, max_length=100)


class InteractionCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    medications: list[MedicationInput] = Field(min_length=1, max_length=20)


class ResolvedMedication(BaseModel):
    input_name: str
    ingredient_ids: list[str]
    canonical_names: list[str]
    rxcui: str | None = None
    resolution: str
    product_ids: list[str] = Field(default_factory=list)
    product_set_ids: list[str] = Field(default_factory=list)


class LabelSectionPreview(BaseModel):
    section: str
    passage: str
    excerpted: bool


class MedicationLabelGuidance(BaseModel):
    ingredient_id: str
    source_name: str
    product_name: str | None
    document_version: str | None
    source_url: HttpUrl
    sections: list[LabelSectionPreview]


class InteractionCheckResponse(BaseModel):
    medications: list[ResolvedMedication]
    interactions: list[InteractionRule]
    timing_restrictions: list[InteractionRule]
    food_interactions: list[InteractionRule]
    beverage_interactions: list[InteractionRule]
    preliminary_findings: list[InteractionRule]
    label_mentions: list[InteractionRule]
    label_guidance: list[MedicationLabelGuidance]
    duplicate_ingredients: list[dict[str, object]]
    coverage_gaps: list[dict[str, str]]
    sources: list[SourcePassage]


class RuleReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_status: ValidationStatus
    expected_status: ValidationStatus
    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def valid_review_target(self) -> "RuleReviewRequest":
        if self.target_status == ValidationStatus.EXTRACTED:
            raise ValueError("review cannot transition a rule back to extracted")
        return self


class AuthenticatedRuleReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_status: ValidationStatus
    expected_status: ValidationStatus
    comment: str = Field(min_length=3, max_length=2000)


class ReviewNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(pattern=r"^(correction|clarification)$")
    expected_status: ValidationStatus
    comment: str = Field(min_length=3, max_length=2000)


class RuleReviewEvent(BaseModel):
    event_id: str
    interaction_id: str
    previous_status: ValidationStatus
    new_status: ValidationStatus
    reviewer: str
    note: str
    reviewed_at: datetime


class ReviewQueueResponse(BaseModel):
    rules: list[InteractionRule]
    total: int
    limit: int
    offset: int


class ReviewSummaryResponse(BaseModel):
    extracted: int
    source_span_verified: int
    human_reviewed: int
    rejected: int


class RuleDetailResponse(BaseModel):
    rule: InteractionRule
    source_name: str
    document_version: str | None
    set_id: str | None
    product_name: str | None
    source_match: bool
    history: list[RuleReviewEvent]

