from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.pipeline import ingest_seed  # noqa: E402
from app.storage.sqlite import SQLiteEvidenceRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the deterministic MedGuide seed corpus")
    parser.add_argument("--database", type=Path, default=Path("var/evidence.sqlite3"))
    parser.add_argument("--fixtures", type=Path, default=Path("data/fixtures"))
    args = parser.parse_args()
    reports = ingest_seed(args.fixtures, SQLiteEvidenceRepository(args.database))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()

