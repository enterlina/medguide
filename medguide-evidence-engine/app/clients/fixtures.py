from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from app.models.domain import (
    ClinicalTrialRecord,
    FetchStatus,
    NormalizedRecord,
    PublicationRecord,
    SourceName,
    SourceSnapshot,
)


class FixtureSourceClient:
    def __init__(self, source: SourceName, fixture_root: Path, parser_version: str = "fixture-v1"):
        self.source = source
        self.fixture_root = fixture_root
        self.parser_version = parser_version

    def fetch(self, external_ids: list[str]) -> Iterable[NormalizedRecord]:
        source_directory = {
            SourceName.PUBMED: "pubmed",
            SourceName.PMC: "pmc",
            SourceName.CLINICAL_TRIALS: "clinicaltrials",
        }[self.source]
        for external_id in external_ids:
            path = self.fixture_root / "raw" / source_directory / f"{external_id}.json"
            raw_bytes = path.read_bytes()
            payload = json.loads(raw_bytes)
            metadata = payload.pop("_snapshot")
            snapshot = SourceSnapshot(
                source=self.source,
                external_id=external_id,
                retrieved_at=datetime.fromisoformat(metadata["retrieved_at"]),
                source_updated_at=(
                    datetime.fromisoformat(metadata["source_updated_at"])
                    if metadata.get("source_updated_at")
                    else None
                ),
                content_hash=hashlib.sha256(raw_bytes).hexdigest(),
                license=metadata.get("license"),
                raw_location=str(path.relative_to(self.fixture_root.parent.parent)),
                parser_version=self.parser_version,
                fetch_status=FetchStatus(metadata["fetch_status"]),
                source_uri=metadata["source_uri"],
            )
            if self.source in (SourceName.PUBMED, SourceName.PMC):
                yield NormalizedRecord(snapshot=snapshot, publication=PublicationRecord(**payload))
            else:
                yield NormalizedRecord(snapshot=snapshot, trial=ClinicalTrialRecord(**payload))

