# Hackathon change log

## Before October 26, 2026

The workspace contained an existing MedGuide medication-management UI prototype. The supplied
specification also described prior FilmScope educational notebook work, but those notebook files and
artifacts were unavailable here.

## New local work on October 26, 2026

- Isolated evidence ingestion package and immutable offline provenance fixtures.
- Section-aware chunking, deterministic embedding interface, exact vector search, BM25, chunk-level
  RRF, metadata filters, deterministic reranking, citation objects, and abstention checks.
- Frozen ten-question engineering fixture and versioned evaluation reporting.
- Explicit Nebius Token Factory adapter/configuration with no mislabeled fallback.
- Evidence Lens UI route preserving all existing MedGuide routes.
- MIT license, notices, data-source disclosure, model/experiment/GPU documentation, and storyboard.

Authenticated Nebius model discovery and a backend Nemotron synthesis call were completed on
October 26, 2026. The sanitized successful trace and prior failures are retained under
`artifacts/nebius-hackathon/`. Semantic citation review is still required. Deployment, public
repository, video, Devpost submission, and CUDA execution are not completed.

Citation validation now combines deterministic citation-ID/range checks, numeric preservation,
lexical claim-to-passage coverage, and a separate model-assisted claim audit. A model verdict cannot
override a failed deterministic guard, and all passing output remains `human_reviewed=false`.

The application was deployed to Vercel under `medguide1/medguide`. Anonymous checks returned HTTP
200 for the root and Evidence Lens pages, and the public backend completed a real Nemotron request.
Production evidence is stored in `artifacts/deployment/production.json`.

