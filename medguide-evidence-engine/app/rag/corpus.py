from __future__ import annotations

import json
from pathlib import Path

from app.rag.chunker import E5_MAX_INPUT_TOKENS, TokenCounter, make_chunks
from app.rag.models import Chunk, Document


MAX_CORPUS_CHUNKS = 500


def load_documents(path: Path) -> list[Document]:
    return [Document.model_validate(item) for item in json.loads(path.read_text())]


def build_chunks_with_report(
    path: Path,
    target_tokens: int = 480,
    overlap_tokens: int = 64,
    max_chunks: int = MAX_CORPUS_CHUNKS,
    *,
    token_counter: TokenCounter | None = None,
    max_input_tokens: int = E5_MAX_INPUT_TOKENS,
) -> tuple[list[Chunk], dict]:
    """Select whole documents in manifest order; never truncate an article silently."""
    selected: list[Chunk] = []
    included: list[str] = []
    excluded: list[dict[str, str | int]] = []
    for document in load_documents(path):
        document_chunks = make_chunks(
            document,
            target_tokens,
            overlap_tokens,
            token_counter=token_counter,
            max_input_tokens=max_input_tokens,
        )
        if len(selected) + len(document_chunks) > max_chunks:
            excluded.append(
                {
                    "source_document_id": document.source_document_id,
                    "reason": "whole_document_would_exceed_chunk_cap",
                    "chunk_count": len(document_chunks),
                }
            )
            continue
        selected.extend(document_chunks)
        included.append(document.source_document_id)
    return selected, {
        "rule": "seed_manifest_order_whole_documents_only",
        "max_chunks": max_chunks,
        "actual_chunks": len(selected),
        "included_source_document_ids": included,
        "exclusions": excluded,
    }


def build_chunks(path: Path, target_tokens: int = 480, overlap_tokens: int = 64) -> list[Chunk]:
    return build_chunks_with_report(path, target_tokens, overlap_tokens)[0]

