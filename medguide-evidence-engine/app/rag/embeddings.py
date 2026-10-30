from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from app.rag.models import Chunk
from app.rag.chunker import embedding_input


class EmbeddingProvider(Protocol):
    model_id: str
    revision: str
    dimension: int
    normalized: bool

    def embed_passages(self, chunks: list[Chunk]) -> np.ndarray: ...

    def embed_query(self, query: str) -> np.ndarray: ...


class FixedHashEmbeddingProvider:
    """Deterministic offline fixture embedding; not a model-quality benchmark."""

    model_id = "fixed-hash-token-v1"
    revision = "1"
    normalized = True

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm else vector

    def embed_passages(self, chunks: list[Chunk]) -> np.ndarray:
        return np.stack(
            [self._embed(embedding_input(chunk.title, chunk.section, chunk.text)) for chunk in chunks]
        )

    def embed_query(self, query: str) -> np.ndarray:
        return self._embed(f"query: {query}")


class SentenceTransformerEmbeddingProvider:
    """Real E5-compatible inference provider; model loading is explicit and offline-capable."""

    normalized = True

    def __init__(
        self,
        model_path: str | Path,
        *,
        model_id: str,
        revision: str,
        device: str = "cpu",
        batch_size: int = 16,
    ):
        from sentence_transformers import SentenceTransformer

        self.model_id = model_id
        self.revision = revision
        self.batch_size = batch_size
        self.model = SentenceTransformer(
            str(model_path), device=device, local_files_only=True
        )
        self.tokenizer = self.model.tokenizer
        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            raise ValueError("embedding model did not expose its output dimension")
        self.dimension = int(dimension)

    def count(self, text: str, *, add_special_tokens: bool = True) -> int:
        return len(
            self.tokenizer(
                text,
                add_special_tokens=add_special_tokens,
                truncation=False,
            )["input_ids"]
        )

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        result = np.asarray(vectors, dtype=np.float32)
        validate_vectors(result, self.dimension)
        return result

    def embed_passages(self, chunks: list[Chunk]) -> np.ndarray:
        return self._encode(
            [embedding_input(chunk.title, chunk.section, chunk.text) for chunk in chunks]
        )

    def embed_query(self, query: str) -> np.ndarray:
        return self._encode([f"query: {query}"])[0]


def validate_vectors(vectors: np.ndarray, expected_dimension: int) -> None:
    if vectors.ndim != 2 or vectors.shape[1] != expected_dimension:
        raise ValueError(
            f"embedding dimension mismatch: expected {expected_dimension}, got {vectors.shape}"
        )
    norms = np.linalg.norm(vectors, axis=1)
    if any(not math.isclose(float(norm), 1.0, rel_tol=1e-4) for norm in norms if norm):
        raise ValueError("embedding provider declared normalized vectors but returned non-unit vectors")

