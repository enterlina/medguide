# Source policies

- PubMed records: NCBI E-utilities ESearch/EFetch only; identify the tool and contact email when
  network access is enabled; honor NCBI rate limits and retry guidance.
- PMC: official PMC interfaces only. Full-text reuse requires recorded access/license metadata.
  PubMed abstracts are never represented as full text.
- ClinicalTrials.gov: API v2 only. Registration, posted results, and peer-reviewed publication are
  separate states.
- Publisher paywalls are never scraped.
- Raw source snapshots are append-only and identified by SHA-256 content hash.

The offline files are compact normalized snapshots derived from official records, not a substitute
for source-of-truth records. Stable source URLs are retained for verification.

