# Canonical hackathon MVP task

This is the single current implementation task. Earlier M0/M1 stop instructions are historical and
do not govern hackathon delivery.

Implement one bounded MedGuide Evidence Lens workflow while preserving existing app behavior:

1. Ingest the fixed PubMed/PMC/ClinicalTrials.gov corpus, then extract, validate, and store facts.
2. On a user question, retrieve with dense top-20 plus BM25 top-20, fuse by chunk ID with RRF,
   rerank the top 20, and pass the top 5 complete source fragments to synthesis.
3. Run a real backend-only NVIDIA Nemotron request through Nebius Token Factory when credentials and
   an authenticated model capability check are available. Never expose the key or mislabel fallback.
4. Validate citations and display inspectable sources, scope, unknowns, and distinct result states:
   supporting, contradicting, no statistically significant effect detected, uncertain, not directly
   applicable, and results not posted in registry. Search linked publications separately.
5. Maintain offline CI plus the Nebius hackathon profile. CUDA, other providers, and extended
   experiments are post-hackathon work.
6. Save reproducible manifests, honest evaluation artifacts, licensing/disclosure materials, and a
   readiness checklist. Do not deploy, publish, upload, provision paid resources, or submit without
   explicit authorization.

Stop only when credentials or a consequential user decision is required. Never fabricate provider
usage, scientific results, benchmark scores, deployment, or submission state.

Submission deadline: October 30, 2026 at 12:00 America/Chicago (Memphis), equivalent to 10:00 PDT
and 17:00 UTC. Recheck the official rules immediately before submission.

