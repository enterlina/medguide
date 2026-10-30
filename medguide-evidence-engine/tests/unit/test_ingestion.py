from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.ingestion.pipeline import ingest_seed
from app.models.domain import (
    ClinicalTrialRecord,
    FetchStatus,
    NormalizedRecord,
    PublicationRecord,
    SourceName,
    SourceSnapshot,
)
from app.storage.sqlite import SQLiteEvidenceRepository


FIXTURES = Path(__file__).parents[2] / "data" / "fixtures"


def scalar(database: Path, query: str) -> int:
    with sqlite3.connect(database) as connection:
        return int(connection.execute(query).fetchone()[0])


def test_seed_ingestion_is_capped_idempotent_and_deduplicated(tmp_path: Path) -> None:
    database = tmp_path / "evidence.sqlite3"
    repository = SQLiteEvidenceRepository(database)

    first = ingest_seed(FIXTURES, repository)
    second = ingest_seed(FIXTURES, repository)

    assert sum(report["records_seen"] for report in first) == 6
    assert sum(report["snapshots_created"] for report in first) == 6
    assert sum(report["snapshots_created"] for report in second) == 0
    assert sum(report["unchanged_records"] for report in second) == 6
    assert scalar(database, "SELECT COUNT(*) FROM publications") == 3
    assert scalar(database, "SELECT COUNT(*) FROM clinical_trials") == 2
    assert scalar(database, "SELECT COUNT(*) FROM source_snapshots") == 6


def test_provenance_keeps_pubmed_and_pmc_snapshots_distinct(tmp_path: Path) -> None:
    database = tmp_path / "evidence.sqlite3"
    repository = SQLiteEvidenceRepository(database)
    ingest_seed(FIXTURES, repository)

    with repository.connect() as connection:
        snapshots = connection.execute(
            "SELECT source, external_id, fetch_status, source_uri FROM source_snapshots "
            "WHERE external_id IN ('23853635', 'PMC3703169') ORDER BY source"
        ).fetchall()
        publication = connection.execute(
            "SELECT pmid, pmcid FROM publications WHERE pmid='23853635'"
        ).fetchone()

    assert [(row["source"], row["fetch_status"]) for row in snapshots] == [
        ("pmc", "fetched"),
        ("pubmed", "abstract_only"),
    ]
    assert publication["pmcid"] == "PMC3703169"


def test_changed_content_creates_snapshot_history(tmp_path: Path) -> None:
    database = tmp_path / "evidence.sqlite3"
    fixture_copy = tmp_path / "fixtures"
    import shutil

    shutil.copytree(FIXTURES, fixture_copy)
    repository = SQLiteEvidenceRepository(database)
    ingest_seed(fixture_copy, repository)

    source_path = fixture_copy / "raw" / "clinicaltrials" / "NCT04642313.json"
    payload = json.loads(source_path.read_text())
    payload["overall_status"] = "COMPLETED"
    payload["_snapshot"]["source_updated_at"] = "2026-10-01T00:00:00+00:00"
    source_path.write_text(json.dumps(payload, indent=2) + "\n")
    ingest_seed(fixture_copy, repository)

    with repository.connect() as connection:
        history = connection.execute(
            "SELECT id, supersedes_snapshot_id FROM source_snapshots "
            "WHERE external_id='NCT04642313' ORDER BY id"
        ).fetchall()
        status = connection.execute(
            "SELECT overall_status FROM clinical_trials WHERE nct_id='NCT04642313'"
        ).fetchone()[0]
    assert len(history) == 2
    assert history[1]["supersedes_snapshot_id"] == history[0]["id"]
    assert status == "COMPLETED"


def test_exact_nct_identifier_links_without_merging_evidence(tmp_path: Path) -> None:
    database = tmp_path / "evidence.sqlite3"
    repository = SQLiteEvidenceRepository(database)
    repository.initialize()
    now = datetime.now(UTC)

    def snapshot(source: SourceName, external_id: str, digest: str) -> SourceSnapshot:
        return SourceSnapshot(
            source=source,
            external_id=external_id,
            retrieved_at=now,
            content_hash=digest * 64,
            raw_location=f"fixture/{external_id}.json",
            parser_version="test-v1",
            fetch_status=FetchStatus.FETCHED,
            source_uri=f"https://example.invalid/{external_id}",
        )

    publication = NormalizedRecord(
        snapshot=snapshot(SourceName.PUBMED, "12345678", "a"),
        publication=PublicationRecord(
            pmid="12345678",
            title="Identifier-link fixture",
            registry_ids=["NCT00000001"],
        ),
    )
    trial = NormalizedRecord(
        snapshot=snapshot(SourceName.CLINICAL_TRIALS, "NCT00000001", "b"),
        trial=ClinicalTrialRecord(
            nct_id="NCT00000001",
            title="Identifier-link registry fixture",
            overall_status="COMPLETED",
            has_results=False,
        ),
    )
    repository.ingest([publication], "test", 1)
    repository.ingest([trial], "test", 1)

    assert scalar(database, "SELECT COUNT(*) FROM publication_trial_links") == 1
    assert scalar(database, "SELECT COUNT(*) FROM publications") == 1
    assert scalar(database, "SELECT COUNT(*) FROM clinical_trials") == 1


def test_repository_rejects_records_above_cap(tmp_path: Path) -> None:
    repository = SQLiteEvidenceRepository(tmp_path / "evidence.sqlite3")
    repository.initialize()
    now = datetime.now(UTC)
    records = [
        NormalizedRecord(
            snapshot=SourceSnapshot(
                source=SourceName.PUBMED,
                external_id=str(10000000 + index),
                retrieved_at=now,
                content_hash=str(index) * 64,
                raw_location=f"fixture/{index}.json",
                parser_version="test-v1",
                fetch_status=FetchStatus.ABSTRACT_ONLY,
                source_uri=f"https://example.invalid/{index}",
            ),
            publication=PublicationRecord(
                pmid=str(10000000 + index), title=f"Fixture {index}"
            ),
        )
        for index in (1, 2)
    ]
    with pytest.raises(ValueError, match="above cap"):
        repository.ingest(records, "test", 1)

