# MedGuide Evidence Lens model card

Offline CI uses a deterministic signed hashing vectorizer and lexical reranker. These are fixtures
for correctness and provenance tests, not biomedical embedding models.

The hackathon adapter uses `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` through Nebius Token Factory.
An authenticated catalog check and backend runtime request succeeded on 2026-10-26. This model
returns visible output in the OpenAI-compatible `message.reasoning` field when `reasoning_effort` is
`none`; the adapter records the selected response field and fails explicitly when all supported
fields are empty. No fallback is labeled as Nebius.

All generated output is a research preview requiring review. The system must not give personalized
medical advice, dosing, safety clearance, automatic GRADE ratings, or numeric MedIndex scores.

