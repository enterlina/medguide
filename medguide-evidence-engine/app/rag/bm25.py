from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

import numpy as np


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KeywordSearch(Protocol):
    def scores(self, query: str) -> np.ndarray: ...


class BM25Index:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.documents = [tokenize(document) for document in documents]
        self.counts = [Counter(document) for document in self.documents]
        self.k1 = k1
        self.b = b
        self.average_length = sum(map(len, self.documents)) / max(len(self.documents), 1)
        self.document_frequency = Counter(
            token for document in self.documents for token in set(document)
        )

    def scores(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.documents), dtype=np.float32)
        for index, document in enumerate(self.documents):
            for token in tokenize(query):
                frequency = self.counts[index][token]
                if not frequency:
                    continue
                df = self.document_frequency[token]
                inverse = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * len(document) / max(self.average_length, 1)
                )
                scores[index] += inverse * frequency * (self.k1 + 1) / denominator
        return scores

