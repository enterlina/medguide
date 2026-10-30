from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_document_id: str
    source_snapshot: str
    title: str
    source: str
    source_uri: str
    identifiers: dict[str, str]
    metadata: dict[str, Any]
    sections: list[dict[str, str]]


class Chunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    source_document_id: str
    source_snapshot: str
    title: str
    section: str
    ordinal: int = Field(ge=0)
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    content_hash: str
    source_uri: str
    identifiers: dict[str, str]
    metadata: dict[str, Any]


class SearchResult(BaseModel):
    chunk: Chunk
    dense_score: float | None
    bm25_score: float | None
    rrf_score: float
    rerank_score: float


class Citation(BaseModel):
    chunk_id: str
    source_document_id: str
    source_uri: str
    quote: str


class Answer(BaseModel):
    status: str
    question: str
    answer: str
    citations: list[Citation]
    limitations: list[str]
    conflicts: list[str]
    corpus_as_of: str
    retrieval_metadata: dict[str, Any]

