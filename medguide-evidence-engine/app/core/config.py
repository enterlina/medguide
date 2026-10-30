from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("MEDGUIDE_DATABASE_PATH", "var/evidence.sqlite3"))
    fixture_root: Path = Path(os.getenv("MEDGUIDE_FIXTURE_ROOT", "data/fixtures"))
    pubmed_max_records: int = int(os.getenv("MEDGUIDE_PUBMED_MAX_RECORDS", "20"))
    pmc_max_records: int = int(os.getenv("MEDGUIDE_PMC_MAX_RECORDS", "10"))
    clinical_trials_max_records: int = int(
        os.getenv("MEDGUIDE_CLINICAL_TRIALS_MAX_RECORDS", "10")
    )

    def cap_for(self, source: str) -> int:
        return {
            "pubmed": self.pubmed_max_records,
            "pmc": self.pmc_max_records,
            "clinicaltrials.gov": self.clinical_trials_max_records,
        }[source]

