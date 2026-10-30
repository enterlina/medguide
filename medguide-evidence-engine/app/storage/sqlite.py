from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from app.models.domain import NormalizedRecord


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    max_records INTEGER NOT NULL CHECK (max_records >= 0),
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    snapshots_created INTEGER NOT NULL DEFAULT 0,
    unchanged_records INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
CREATE TABLE IF NOT EXISTS source_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    source_updated_at TEXT,
    license TEXT,
    raw_location TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    fetch_status TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    ingestion_run_id TEXT NOT NULL REFERENCES ingestion_runs(id),
    supersedes_snapshot_id INTEGER REFERENCES source_snapshots(id),
    UNIQUE(source, external_id, content_hash)
);
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT NOT NULL UNIQUE,
    pmcid TEXT UNIQUE,
    doi TEXT UNIQUE,
    title TEXT NOT NULL,
    journal TEXT,
    publication_year INTEGER,
    publication_types TEXT NOT NULL,
    current_snapshot_id INTEGER NOT NULL REFERENCES source_snapshots(id)
);
CREATE TABLE IF NOT EXISTS clinical_trials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    enrollment INTEGER,
    enrollment_type TEXT,
    has_results INTEGER NOT NULL,
    peer_reviewed_publication INTEGER NOT NULL,
    current_snapshot_id INTEGER NOT NULL REFERENCES source_snapshots(id)
);
CREATE TABLE IF NOT EXISTS publication_trial_links (
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    trial_id INTEGER NOT NULL REFERENCES clinical_trials(id),
    relationship TEXT NOT NULL,
    verified_by TEXT NOT NULL,
    PRIMARY KEY(publication_id, trial_id, relationship)
);
CREATE TABLE IF NOT EXISTS pending_registry_links (
    pmid TEXT NOT NULL,
    nct_id TEXT NOT NULL,
    PRIMARY KEY(pmid, nct_id)
);
"""


class SQLiteEvidenceRepository:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def ingest(
        self,
        records: Iterable[NormalizedRecord],
        query: str,
        max_records: int,
    ) -> dict[str, int | str]:
        materialized = list(records)
        if len(materialized) > max_records:
            raise ValueError(f"source returned {len(materialized)} records above cap {max_records}")
        if not materialized:
            raise ValueError("an ingestion run must contain at least one record")

        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        source = materialized[0].snapshot.source.value
        counts = {"records_seen": 0, "snapshots_created": 0, "unchanged_records": 0}
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO ingestion_runs(id, source, query, max_records, status, started_at) "
                "VALUES (?, ?, ?, ?, 'running', ?)",
                (run_id, source, query, max_records, started_at),
            )
            try:
                for record in materialized:
                    if record.snapshot.source.value != source:
                        raise ValueError("one ingestion run cannot mix sources")
                    counts["records_seen"] += 1
                    snapshot_id, created = self._upsert_snapshot(connection, run_id, record)
                    counts["snapshots_created" if created else "unchanged_records"] += 1
                    if record.publication:
                        self._upsert_publication(connection, snapshot_id, record)
                    if record.trial:
                        self._upsert_trial(connection, snapshot_id, record)
                self._link_verified_registry_ids(connection)
                connection.execute(
                    "UPDATE ingestion_runs SET status='completed', completed_at=?, records_seen=?, "
                    "snapshots_created=?, unchanged_records=? WHERE id=?",
                    (
                        datetime.now(UTC).isoformat(),
                        counts["records_seen"],
                        counts["snapshots_created"],
                        counts["unchanged_records"],
                        run_id,
                    ),
                )
            except Exception as exc:
                connection.execute(
                    "UPDATE ingestion_runs SET status='failed', completed_at=?, error=? WHERE id=?",
                    (datetime.now(UTC).isoformat(), str(exc), run_id),
                )
                raise
        return {"run_id": run_id, **counts}

    def _upsert_snapshot(
        self, connection: sqlite3.Connection, run_id: str, record: NormalizedRecord
    ) -> tuple[int, bool]:
        snapshot = record.snapshot
        existing = connection.execute(
            "SELECT id FROM source_snapshots WHERE source=? AND external_id=? AND content_hash=?",
            (snapshot.source.value, snapshot.external_id, snapshot.content_hash),
        ).fetchone()
        if existing:
            return int(existing["id"]), False
        previous = connection.execute(
            "SELECT id FROM source_snapshots WHERE source=? AND external_id=? "
            "ORDER BY id DESC LIMIT 1",
            (snapshot.source.value, snapshot.external_id),
        ).fetchone()
        cursor = connection.execute(
            """INSERT INTO source_snapshots(
                source, external_id, retrieved_at, content_hash, source_updated_at, license,
                raw_location, parser_version, fetch_status, source_uri, ingestion_run_id,
                supersedes_snapshot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snapshot.source.value,
                snapshot.external_id,
                snapshot.retrieved_at.isoformat(),
                snapshot.content_hash,
                snapshot.source_updated_at.isoformat() if snapshot.source_updated_at else None,
                snapshot.license,
                snapshot.raw_location,
                snapshot.parser_version,
                snapshot.fetch_status.value,
                str(snapshot.source_uri),
                run_id,
                int(previous["id"]) if previous else None,
            ),
        )
        return int(cursor.lastrowid), True

    @staticmethod
    def _upsert_publication(
        connection: sqlite3.Connection, snapshot_id: int, record: NormalizedRecord
    ) -> None:
        import json

        publication = record.publication
        assert publication is not None
        connection.execute(
            """INSERT INTO publications(
                pmid, pmcid, doi, title, journal, publication_year, publication_types,
                current_snapshot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pmid) DO UPDATE SET
                pmcid=COALESCE(excluded.pmcid, publications.pmcid),
                doi=COALESCE(excluded.doi, publications.doi), title=excluded.title,
                journal=excluded.journal, publication_year=excluded.publication_year,
                publication_types=excluded.publication_types,
                current_snapshot_id=excluded.current_snapshot_id""",
            (
                publication.pmid,
                publication.pmcid,
                publication.doi,
                publication.title,
                publication.journal,
                publication.publication_year,
                json.dumps(publication.publication_types, sort_keys=True),
                snapshot_id,
            ),
        )
        for nct_id in publication.registry_ids:
            connection.execute(
                "INSERT OR IGNORE INTO pending_registry_links(pmid, nct_id) VALUES (?, ?)",
                (publication.pmid, nct_id),
            )

    @staticmethod
    def _upsert_trial(
        connection: sqlite3.Connection, snapshot_id: int, record: NormalizedRecord
    ) -> None:
        trial = record.trial
        assert trial is not None
        connection.execute(
            """INSERT INTO clinical_trials(
                nct_id, title, overall_status, enrollment, enrollment_type, has_results,
                peer_reviewed_publication, current_snapshot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nct_id) DO UPDATE SET title=excluded.title,
                overall_status=excluded.overall_status, enrollment=excluded.enrollment,
                enrollment_type=excluded.enrollment_type, has_results=excluded.has_results,
                peer_reviewed_publication=excluded.peer_reviewed_publication,
                current_snapshot_id=excluded.current_snapshot_id""",
            (
                trial.nct_id,
                trial.title,
                trial.overall_status,
                trial.enrollment,
                trial.enrollment_type,
                int(trial.has_results),
                int(trial.peer_reviewed_publication),
                snapshot_id,
            ),
        )

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    @staticmethod
    def _link_verified_registry_ids(connection: sqlite3.Connection) -> None:
        # Exact registry links are added by the pipeline after both source runs are present.
        connection.execute(
            """INSERT OR IGNORE INTO publication_trial_links(
                publication_id, trial_id, relationship, verified_by
            ) SELECT p.id, t.id, 'registry_identifier', 'exact_nct_id'
              FROM pending_registry_links l
              JOIN publications p ON p.pmid=l.pmid
              JOIN clinical_trials t ON t.nct_id=l.nct_id"""
        )

