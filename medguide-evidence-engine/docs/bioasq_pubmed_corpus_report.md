# BioASQ 14b pooled PubMed corpus

PubMed records were downloaded from the official NCBI EFetch API for the unique gold PMIDs in
BioASQ 14b. The downloader is batch-based, rate-limited, resumable and validates JSONL integrity.

| Measure | Count |
| --- | ---: |
| Requested unique gold PMIDs | 58,048 |
| PubMed records returned | 57,984 |
| Records with abstracts | 57,940 |
| PMIDs not returned by NCBI | 64 |

The local JSONL corpus is stored at
`data/external/bioasq14b/pubmed_abstracts.jsonl`; provenance and completeness are recorded in
`data/external/bioasq14b/download_manifest.json`.

The metadata-complete refresh is stored separately as `pubmed_abstracts_v2.jsonl` with
`download_manifest_v2.json`; it adds publication year and journal without overwriting the original.
Of 5,729 BioASQ questions, 5,636 have complete gold-document abstract coverage. The fixed pilot uses
seed `20261028` and 200 questions, balanced as 50 per question type.

## Scope warning

This is a pooled corpus formed from documents judged relevant to at least one BioASQ training
question. It is not the official full-PubMed BioASQ/BEIR retrieval collection. Metrics produced from
this pool must be labeled `BioASQ 14b pooled-gold benchmark` and must not be compared directly with
official leaderboard scores.
