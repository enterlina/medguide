from __future__ import annotations

import re

from app.rag.bm25 import BM25Index, tokenize
from app.rag.embeddings import EmbeddingProvider
from app.rag.models import Chunk, SearchResult
from app.rag.vector_store import ExactVectorStore


def _matches(chunk: Chunk, filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        actual = chunk.metadata.get(key)
        if isinstance(actual, list):
            if expected not in actual:
                return False
        elif str(actual).lower() != expected.lower():
            return False
    return True


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], embeddings: EmbeddingProvider):
        self.chunks = chunks
        self.embeddings = embeddings
        self.vectors = embeddings.embed_passages(chunks)
        self.vector_store = ExactVectorStore(self.vectors)
        self.bm25 = BM25Index([chunk.text for chunk in chunks])

    def search(
        self,
        query: str,
        filters: dict[str, str] | None = None,
        top_k: int = 5,
        candidate_k: int = 20,
        rerank_k: int = 20,
        per_document_cap: int = 2,
    ) -> list[SearchResult]:
        allowed = {
            index for index, chunk in enumerate(self.chunks) if _matches(chunk, filters or {})
        }
        dense = self.vector_store.search(self.embeddings.embed_query(query), len(self.chunks))
        lexical_scores = self.bm25.scores(query)
        lexical = sorted(enumerate(lexical_scores), key=lambda item: -item[1])
        dense = [(index, score) for index, score in dense if index in allowed][:candidate_k]
        lexical = [(index, float(score)) for index, score in lexical if index in allowed][:candidate_k]
        fused: dict[int, float] = {}
        for ranking in (dense, lexical):
            for rank, (index, _) in enumerate(ranking, start=1):
                fused[index] = fused.get(index, 0.0) + 1.0 / (60 + rank)
        dense_map = dict(dense)
        lexical_map = dict(lexical)
        query_tokens = set(tokenize(query))
        candidates = []
        for index, rrf_score in fused.items():
            chunk_tokens = set(tokenize(self.chunks[index].text))
            overlap = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
            phrase_bonus = 0.2 if re.sub(r"\W+", " ", query.lower()).strip() in self.chunks[index].text.lower() else 0
            candidates.append(
                SearchResult(
                    chunk=self.chunks[index],
                    dense_score=dense_map.get(index),
                    bm25_score=lexical_map.get(index),
                    rrf_score=rrf_score,
                    rerank_score=overlap + phrase_bonus + rrf_score,
                )
            )
        candidates.sort(key=lambda result: -result.rrf_score)
        candidates = candidates[:rerank_k]
        candidates.sort(key=lambda result: -result.rerank_score)
        selected: list[SearchResult] = []
        document_counts: dict[str, int] = {}
        for result in candidates:
            count = document_counts.get(result.chunk.source_document_id, 0)
            if count >= per_document_cap:
                continue
            selected.append(result)
            document_counts[result.chunk.source_document_id] = count + 1
            if len(selected) == top_k:
                break
        return selected

