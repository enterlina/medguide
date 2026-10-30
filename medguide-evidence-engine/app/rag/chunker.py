from __future__ import annotations

import hashlib
import re
from typing import Protocol

from app.rag.models import Chunk, Document


TOKEN_PATTERN = re.compile(r"\S+")
E5_MAX_INPUT_TOKENS = 512


class TokenCounter(Protocol):
    def count(self, text: str, *, add_special_tokens: bool = True) -> int: ...


class WhitespaceTokenCounter:
    """Offline boundary fixture. Real E5 runs must inject the model tokenizer."""

    def count(self, text: str, *, add_special_tokens: bool = True) -> int:
        return len(TOKEN_PATTERN.findall(text)) + (2 if add_special_tokens else 0)


def embedding_input(title: str, section: str, text: str) -> str:
    return f"passage: {title}\nsection: {section}\n{text}"


def _token_spans(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in TOKEN_PATTERN.finditer(text)]


def make_chunks(
    document: Document,
    target_tokens: int = 480,
    overlap_tokens: int = 64,
    *,
    max_input_tokens: int = E5_MAX_INPUT_TOKENS,
    token_counter: TokenCounter | None = None,
) -> list[Chunk]:
    if target_tokens <= overlap_tokens or overlap_tokens < 0:
        raise ValueError("target_tokens must exceed nonnegative overlap_tokens")
    counter = token_counter or WhitespaceTokenCounter()
    chunks: list[Chunk] = []
    ordinal = 0
    document_cursor = 0
    for section_entry in document.sections:
        section = section_entry["section"]
        text = section_entry["text"].strip()
        spans = _token_spans(text)
        if not spans:
            document_cursor += len(text) + 1
            continue
        start_token = 0
        while start_token < len(spans):
            end_token = min(start_token + target_tokens, len(spans))
            while end_token > start_token:
                candidate = text[spans[start_token][0] : spans[end_token - 1][1]]
                if counter.count(embedding_input(document.title, section, candidate)) <= max_input_tokens:
                    break
                end_token -= 1
            if end_token == start_token:
                raise ValueError(
                    f"embedding metadata alone exhausts the {max_input_tokens}-token input budget "
                    f"for {document.source_document_id}/{section}; truncation is forbidden"
                )
            local_start = spans[start_token][0]
            local_end = spans[end_token - 1][1]
            chunk_text = text[local_start:local_end]
            digest = hashlib.sha256(chunk_text.encode()).hexdigest()
            chunks.append(
                Chunk(
                    chunk_id=f"{document.source_snapshot}:{section}:{ordinal}:{digest[:12]}",
                    source_document_id=document.source_document_id,
                    source_snapshot=document.source_snapshot,
                    title=document.title,
                    section=section,
                    ordinal=ordinal,
                    text=chunk_text,
                    char_start=document_cursor + local_start,
                    char_end=document_cursor + local_end,
                    content_hash=digest,
                    source_uri=document.source_uri,
                    identifiers=document.identifiers,
                    metadata=document.metadata,
                )
            )
            ordinal += 1
            if counter.count(embedding_input(document.title, section, chunk_text)) > max_input_tokens:
                raise AssertionError("chunk construction exceeded the embedding input budget")
            if end_token == len(spans):
                break
            start_token = end_token - overlap_tokens
        document_cursor += len(text) + 1
    return chunks

