# Submission readiness

| Item | Status | Evidence |
| --- | --- | --- |
| Bounded source fixtures and provenance | done | seed manifest, ingestion report, tests |
| Chunk-level hybrid retrieval | done | RAG modules and offline evaluation |
| Source-traceable medication cards | done | Searchable/collapsible Magnesium card, catalog-style evidence specifications, evidence filters and removable saved cards at `/evidence-lens` |
| Medication comparison | done_ui | Explicit add/remove comparison state and grouped side-by-side evidence table; a second reviewed medication dataset is still required to populate two columns |
| Live source update check | done | Backend-only PubMed and ClinicalTrials.gov check; discoveries stay unreviewed until admitted |
| Unknown/gap behavior | done_fixture | gap and filter tests |
| Backend-only key handling | done_local | server route; no `NEXT_PUBLIC_*` secret |
| Admin ingestion/index auth | done_local | explicit admin-token dependency |
| Automated citation validation | done_local_requires_human_review | ID/range, numeric and lexical guards plus model-assisted claim audit |
| Real Nebius/Nemotron runtime | done_requires_review | sanitized runtime trace; three failures retained |
| Frozen-set manual correctness review | not_done | only fixture retrieval metrics exist |
| GPU benchmark | not_done | no hardware execution |
| Deployment/free judge URL | done | https://medguide-orcin.vercel.app/evidence-lens; anonymous HTTP 200 and production source-update API smoke test passed; current deployment `dpl_HEhrwn8A6vzmbPmVH5XSnHfarurP` |
| Public licensed repository | not_done | no Git repository or publication authorization |
| Public under-three-minute video | not_done | storyboard only |
| Actual platform feedback | partial | authenticated runs completed and provider-specific response-field behavior documented; submission feedback text remains to write |
| Team eligibility details | not_done | requires entrant confirmation |
| Devpost submission | not_done | not authorized |

