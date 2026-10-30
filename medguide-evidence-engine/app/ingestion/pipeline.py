from __future__ import annotations

import json
from pathlib import Path

from app.clients.fixtures import FixtureSourceClient
from app.models.domain import SourceName
from app.storage.sqlite import SQLiteEvidenceRepository


def ingest_seed(fixture_root: Path, repository: SQLiteEvidenceRepository) -> list[dict]:
    manifest = json.loads((fixture_root / "seed_manifest.json").read_text())
    repository.initialize()
    reports = []
    for source_entry in manifest["sources"]:
        source = SourceName(source_entry["source"])
        ids = source_entry["external_ids"]
        cap = int(source_entry["cap"])
        if len(ids) > cap:
            raise ValueError(f"manifest IDs for {source} exceed configured cap")
        client = FixtureSourceClient(source, fixture_root)
        report = repository.ingest(client.fetch(ids), manifest["query"], cap)
        reports.append({"source": source.value, **report})
    return reports

