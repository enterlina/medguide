from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class OfficialSourceTransport:
    """Small explicit HTTP transport for later online ingestion; unused by offline tests."""

    timeout_seconds: float = 20.0
    user_agent: str = "medguide-evidence-engine/0.1"

    def get_json(self, base_url: str, params: dict[str, str]) -> dict:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)


PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CLINICAL_TRIALS_V2_URL = "https://clinicaltrials.gov/api/v2/studies"

