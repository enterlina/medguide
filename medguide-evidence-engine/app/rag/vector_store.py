from __future__ import annotations

from typing import Protocol

import numpy as np


class VectorStore(Protocol):
    dimension: int

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[int, float]]: ...


class ExactVectorStore:
    def __init__(self, vectors: np.ndarray):
        if vectors.ndim != 2:
            raise ValueError("vectors must be a 2D matrix")
        self.vectors = vectors
        self.dimension = vectors.shape[1]

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        if query_vector.shape != (self.dimension,):
            raise ValueError(
                f"query dimension mismatch: expected {self.dimension}, got {query_vector.shape}"
            )
        scores = self.vectors @ query_vector
        indices = np.argsort(-scores)[:top_k]
        return [(int(index), float(scores[index])) for index in indices]

