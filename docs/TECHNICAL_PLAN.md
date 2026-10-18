# Technical Plan — MedGuide MVP

**Owner: Kunal Verma** · Status: Proposal, not implemented

## Goal
Implement an evidence-grounded medication review backend with structured results and source references. The application is a research demonstration; it does not provide treatment recommendations.

## Phase 1 — Architecture decision (Oct 18–20)
- Compare 2–3 NVIDIA open-source models supported by Nebius (availability, latency, structured JSON quality, cost).
- Choose licensed medical references, medication name-normalization source, and interaction evidence approach.
- Decide embedding model, retrieval strategy, and vector store (Qdrant is a candidate, not a final choice).
- Document architecture and proposed environment variables without including credential values.
- Agree on API contract with Elena before implementation.

## Phase 2 — First API (Oct 21–23)
- Python/FastAPI service with input validation and medication normalization.
- Initial source-backed retrieval against a small permitted reference corpus.
- Implement POST /api/analyze using docs/API_CONTRACT.md.
- Return ambiguity and insufficient-evidence statuses honestly.

## Phase 3 — Model integration (Oct 24–26)
- Use an eligible NVIDIA open-source model via Nebius Token Factory or Nebius AI Cloud.
- LLM generates explanations *from evidence*, not interaction facts from memory.
- Preserve source URLs/identifiers and uncertainty in the API response.
- Test representative cases: documented interaction, ambiguous drug, missing evidence, conflicting information.

## Phase 4 — Release (Oct 27–29)
- Expose a testable backend to the frontend.
- Add reproducible deployment and local execution steps.
- Capture model details, eval outputs and system limitations.
- Support recorded end-to-end demo.

## Acceptance criteria
- One synthetic multi-medication demo produces a schema-valid response.
- Every factual medication interaction is traceable to evidence.
- Unknown results are not presented as safe.
- Model/Nebius runtime integration is demonstrated, not merely declared.
- No secrets or patient data committed.
