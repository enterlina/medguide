from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.models.domain import NormalizedRecord, SourceName


class SourceClient(Protocol):
    source: SourceName

    def fetch(self, external_ids: list[str]) -> Iterable[NormalizedRecord]: ...


class EvidenceRepository(Protocol):
    def initialize(self) -> None: ...

    def ingest(self, records: Iterable[NormalizedRecord], query: str, max_records: int) -> dict[str, int]: ...

