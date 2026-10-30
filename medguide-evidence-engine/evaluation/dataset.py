from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str
    question: str
    kind: str
    answerable_in_corpus: bool
    relevant_source_document_ids: list[str]
    required_evidence_groups: list[list[str]]
    split: str
    review_status: str


def load_questions(path: Path) -> list[Question]:
    return [Question.model_validate(item) for item in json.loads(path.read_text())]


class UserQuestionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    created_on: str
    version: str
    population: str
    question_count: int
    language: str
    popularity: str


class QuestionSupplement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplement_id: str
    name: str
    category: str
    goal: str
    comparison: str


class UserQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    supplement_id: str
    supplement: str
    category: str
    intent: Literal["effectiveness", "evidence", "dose", "safety_comparison"]
    question: str
    language: str
    expected_sources: str
    evaluation_target: Literal[
        "human_efficacy",
        "pico_study_quality",
        "dose_population_outcome",
        "safety_interactions_comparison",
    ]
    safety_review: bool
    query_origin: Literal["expert_curated_hypothesis"]
    popularity_verified: bool


class UserQuestionDataset(BaseModel):
    """Query hypotheses for evaluation; never evidence or measured popularity data."""

    model_config = ConfigDict(extra="forbid")
    metadata: UserQuestionMetadata
    supplements: list[QuestionSupplement]
    questions: list[UserQuestion]

    @model_validator(mode="after")
    def validate_dataset_links(self) -> UserQuestionDataset:
        supplement_ids = [item.supplement_id for item in self.supplements]
        question_ids = [item.question_id for item in self.questions]
        if len(set(supplement_ids)) != len(supplement_ids):
            raise ValueError("supplement IDs must be unique")
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("question IDs must be unique")
        if self.metadata.question_count != len(self.questions):
            raise ValueError("metadata question_count does not match questions")
        known = set(supplement_ids)
        if unknown := {item.supplement_id for item in self.questions} - known:
            raise ValueError(f"questions reference unknown supplements: {sorted(unknown)}")
        if any(item.popularity_verified for item in self.questions):
            raise ValueError("expert-curated hypotheses cannot be marked popularity-verified")
        return self


def load_user_question_dataset(path: Path) -> UserQuestionDataset:
    return UserQuestionDataset.model_validate_json(path.read_text(encoding="utf-8"))


class GoldenCandidateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str
    supplement_id: str
    supplement: str
    category: str
    query: str
    intent: str
    language: str
    difficulty: Literal["easy", "medium", "hard"]
    challenge_tags: list[str]
    query_context: dict[str, str]
    expected_source_types: list[str]
    candidate_pmids: list[str]
    expected_pmids: list[str]
    relevance_labels: dict[str, int]
    expected_evidence_facts: list[str]
    expected_answer_state: str
    review_status: Literal["pending_human_review", "reviewed"]

    @model_validator(mode="after")
    def ground_truth_requires_review(self) -> GoldenCandidateQuery:
        if self.review_status == "pending_human_review" and (
            self.expected_pmids or self.relevance_labels
        ):
            raise ValueError("unreviewed candidates cannot contain golden relevance judgments")
        if not set(self.expected_pmids).issubset(self.candidate_pmids):
            raise ValueError("expected PMIDs must be present in the reviewed candidate set")
        return self


class GoldenCandidateDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: dict[str, object]
    supplements: list[QuestionSupplement]
    queries: list[GoldenCandidateQuery]

    @model_validator(mode="after")
    def validate_candidate_dataset(self) -> GoldenCandidateDataset:
        if len(self.supplements) != 100 or len(self.queries) != 2000:
            raise ValueError("candidate dataset requires 100 supplements and 2000 queries")
        counts: dict[str, int] = {}
        for query in self.queries:
            counts[query.supplement_id] = counts.get(query.supplement_id, 0) + 1
        if set(counts.values()) != {20}:
            raise ValueError("each selected supplement requires 20 queries")
        return self


def load_golden_candidate_dataset(path: Path) -> GoldenCandidateDataset:
    return GoldenCandidateDataset.model_validate_json(path.read_text(encoding="utf-8"))

