# MedGuide Evidence Engine

Portfolio case study: [docs/portfolio_ai_engineering_case.md](docs/portfolio_ai_engineering_case.md)

This isolated Python package implements bounded ingestion plus an offline retrieval/evaluation path
for MedGuide Evidence Lens. It preserves source provenance, separates registrations from results,
and returns inspectable citations or an insufficient-evidence state. The adjacent Next.js app adds
an `/evidence-lens` view without replacing existing routes.

## MVP storage choice

M1 uses Python's built-in SQLite driver plus Pydantic v2. This keeps the fixture pipeline fully
offline and dependency-light. Repository and client protocols keep persistence and retrieval
replaceable; PostgreSQL/pgvector is deferred until the retrieval milestone. Raw fixture files are
immutable inputs, while SQLite is a rebuildable local artifact.

## Run

From this directory:

```bash
python3 scripts/seed_corpus.py --database var/evidence.sqlite3
python3 scripts/build_index.py --rebuild
python3 scripts/search.py "Does the magnesium gluconate trial have posted results?"
python3 scripts/evaluate.py
uvicorn app.main:app --reload
python3 scripts/benchmark_gpu.py
python3 scripts/run_retrieval_experiment.py
python3 scripts/evaluate_retrieval_annotations.py
python3 -m pytest
python3 -m ruff check .  # when ruff is installed
```

The real retrieval experiment uses locally cached `intfloat/multilingual-e5-base` embeddings and a
separate multilingual MiniLM second-stage reranker. It writes persistent vectors, BM25 state,
ranking JSON/CSV, annotation templates, and an HTML debug viewer under
`artifacts/retrieval-experiment/`. Serve that directory locally (for example with
`python3 -m http.server 8765`) to annotate pooled results. Unreviewed labels never count as
irrelevant, and quality metrics remain unavailable until a complete reviewed pool exists.

The seed query is documented in `data/fixtures/seed_manifest.json`. The bundled corpus contains
three PubMed records, one linked PMC record, and two ClinicalTrials.gov registrations. Fixture
metadata was selected from official source interfaces on 2026-10-26. Tests never use the network.

## Boundaries

- This is research infrastructure, not medical advice or a treatment recommender.
- A registration is not a positive efficacy study; registrations and linked publications remain
  distinct records.
- Unknown or unreported data stays unknown. M1 performs no evidence extraction or synthesis.
- No GRADE rating, MedIndex score, safety clearance, or dosing recommendation is produced.
- Online clients require explicit configuration and are not invoked by the seed command or tests.

## Hackathon runtime status

The competition profile uses `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` through Nebius Token Factory.
Authenticated local and production calls have completed. `NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, and
`NEBIUS_MODEL_ID` remain server-side; the adapter fails explicitly and never relabels a fallback as
Nebius. No CUDA benchmark, public repository, video, or Devpost submission is claimed.

Public demo: https://medguide-orcin.vercel.app/evidence-lens

The design reimplements small patterns identified by the supplied static FilmScope audit. The
notebooks, datasets, checkpoints, and lockfiles were not present and were not copied or executed.
Historic FilmScope results are not MedGuide results. See `docs/reuse_audit.md` and the root
`THIRD_PARTY_NOTICES.md`.

The only current delivery task is `docs/hackathon_mvp_plan.md`. Earlier milestone stop documents are
retained as implementation history, not competing instructions. Required hackathon profiles are
`offline-ci` and `nebius-hackathon`; CUDA and other provider experiments are optional later work.

