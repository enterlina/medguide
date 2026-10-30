from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class SourceName(StrEnum):
    PUBMED = "pubmed"
    PMC = "pmc"
    CLINICAL_TRIALS = "clinicaltrials.gov"


class FetchStatus(StrEnum):
    FETCHED = "fetched"
    ABSTRACT_ONLY = "abstract_only"
    UNSUPPORTED_FULL_TEXT = "unsupported_full_text"


class SourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceName
    external_id: str
    retrieved_at: datetime
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_updated_at: datetime | None = None
    license: str | None = None
    raw_location: str
    parser_version: str
    fetch_status: FetchStatus
    source_uri: HttpUrl


class PublicationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d{1,9}$")
    pmcid: str | None = Field(default=None, pattern=r"^PMC\d+$")
    doi: str | None = None
    title: str = Field(min_length=1)
    journal: str | None = None
    publication_year: int | None = Field(default=None, ge=1600, le=2200)
    publication_types: list[str] = Field(default_factory=list)
    registry_ids: list[str] = Field(default_factory=list)

    @field_validator("registry_ids")
    @classmethod
    def valid_registry_ids(cls, values: list[str]) -> list[str]:
        if any(not value.startswith("NCT") or len(value) != 11 for value in values):
            raise ValueError("registry IDs must use NCT######## format")
        return values


class ClinicalTrialRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str = Field(pattern=r"^NCT\d{8}$")
    title: str = Field(min_length=1)
    overall_status: str
    enrollment: int | None = Field(default=None, ge=0)
    enrollment_type: str | None = None
    interventions: list[dict[str, Any]] = Field(default_factory=list)
    outcomes: list[dict[str, Any]] = Field(default_factory=list)
    has_results: bool
    peer_reviewed_publication: bool = False
    source_updated_at: datetime | None = None


class NormalizedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot: SourceSnapshot
    publication: PublicationRecord | None = None
    trial: ClinicalTrialRecord | None = None

    @field_validator("trial")
    @classmethod
    def source_matches_trial(cls, value: ClinicalTrialRecord | None, info: Any) -> ClinicalTrialRecord | None:
        snapshot = info.data.get("snapshot")
        if value is not None and snapshot and snapshot.source != SourceName.CLINICAL_TRIALS:
            raise ValueError("trial payload requires a ClinicalTrials.gov snapshot")
        return value


class FactVerification(BaseModel):
    """Independent checks; provenance does not establish interpretation correctness."""

    model_config = ConfigDict(extra="forbid")

    schema_valid: bool
    source_span_verified: bool
    human_reviewed: bool
    reviewer_note: str | None = None


class ResultInterpretation(StrEnum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NO_STATISTICALLY_SIGNIFICANT_EFFECT_DETECTED = (
        "no_statistically_significant_effect_detected"
    )
    UNCERTAIN = "uncertain"
    NOT_APPLICABLE = "not_directly_applicable"
    RESULTS_NOT_POSTED_IN_REGISTRY = "results_not_posted_in_registry"

