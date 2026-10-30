# Offline retrieval experiment report

Run the frozen report with `python3 scripts/evaluate.py`. The initial implementation uses 19
section-aware chunks, deterministic fixture vectors, BM25, chunk-level RRF, and a deterministic
token-overlap reranker. It is an engineering smoke test, not a model-quality or clinical benchmark.

The fixed path is dense top-20 plus BM25 top-20, chunk-level RRF, rerank top-20, then context top-5.
Document metrics use `source_document_id` for either a publication/full-text record or an NCT
registration. Trial-family grouping is a separate deduplication concern.

Run `ba3bc75a9a4e8b37` on ten fixed questions reported document Recall@5 1.0, MRR 0.9167,
complete-evidence success 1.0 across eight answerable items, and gap abstention 1.0 on two curated
gap fixtures. These labels were manually authored alongside this implementation and were not
independently clinically reviewed. The tiny corpus, highly lexical questions, and test visibility
make these regression results unsuitable as headline model-quality or deployment-readiness claims.

Real E5/BGE, Nebius generation, controlled gold-context generation, manual correctness review,
paired intervals, and a larger frozen split are not run. Historic FilmScope scores are unrelated.


