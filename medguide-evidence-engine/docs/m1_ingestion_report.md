# M1 seed ingestion report

Historical implementation report. The current hackathon task is
`docs/hackathon_mvp_plan.md`; this file is not an active stop instruction.

Run date: 2026-10-26  
Mode: deterministic offline fixtures  
Query: `(magnesium[Title/Abstract]) AND (sleep[Title/Abstract] OR insomnia[Title/Abstract]) AND humans[MeSH Terms]`

## Actual corpus

| Source | Cap | Ingested snapshots | Canonical records |
| --- | ---: | ---: | ---: |
| PubMed | 20 | 3 | 3 publications |
| PMC | 10 | 1 | linked to an existing publication |
| ClinicalTrials.gov | 10 | 2 | 2 trials |

IDs: PMID 23853635, 33865376, 39252819; PMCID PMC3703169; NCT04642313,
NCT05236504.

No records were excluded from the selected fixture manifest. These are demonstration records, not a
systematic review sample. Both trial fixtures have `has_results=false`; neither is counted as
positive efficacy evidence. The PubMed and PMC snapshots for PMID 23853635 remain distinct while
resolving to one canonical publication.

## Reproducibility result

The first smoke run created six snapshots. Re-running the identical manifest created zero new
snapshots and reported six unchanged records. A fixture update test creates one new snapshot linked
to its predecessor and updates the canonical record without deleting history.

## Known limitations

- The corpus is intentionally tiny and not exhaustive.
- Raw fixtures are compact normalized source snapshots, not archival copies of complete upstream
  payloads.
- Online fetching, retries, and rate-limit coordination need production hardening before scheduled
  ingestion.
- Retraction/correction detection is not yet automated.
- M2 retrieval and M3 evidence extraction are not implemented.

## Historical completion state

M1 was completed under the earlier phased plan. The current implementation proceeds under the
single canonical hackathon task in `docs/hackathon_mvp_plan.md`; there is no M1 approval pause.

