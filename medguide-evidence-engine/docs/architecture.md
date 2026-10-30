# M0 architecture decision

The evidence engine is a sibling package inside the MedGuide workspace. The web prototype is not
replaced. Two processes are intentionally separate:

`ingestion -> immutable snapshot -> normalization -> fact extraction -> validation -> stored facts`

`question -> scoped hybrid retrieval -> reranking -> synthesis -> citation validation -> response`

## Four logical layers

1. **Supplement Catalog** resolves canonical ingredients, scientific names, synonyms, forms, and
   market-specific products. Ingredient evidence is never silently transferred to a branded product.
2. **Evidence Database** stores PICO, dose, duration, results, adverse events, limitations, funding,
   sponsor relationships, risk of bias, verification state, and immutable source provenance.
3. **Vector RAG** stores section-aware chunks linked to a source document and evidence record.
   Retrieval similarity locates context; it is not an evidence-quality score.
4. **Freshness Pipeline** records discovery and source changes before reviewed evidence is updated.
   New records remain candidates until extraction, source-span verification, and human review pass.

The MVP may keep these contracts in SQLite and local vector artifacts. Repository interfaces are the
migration boundary for PostgreSQL, full-text search, and pgvector; changing the database must not
collapse the four logical layers.

`published_at`, `indexed_at`, `source_updated_at`, and `last_checked_at` are distinct timestamps.
`evidence_version` identifies the exact reviewed dataset behind a displayed conclusion or MedIndex.
Daily discovery should trigger processing only for affected ingredients and indications. Live checks
may expose unreviewed candidates, but never merge them into the admitted evidence set.

Each stage is deterministic and retry-safe. The repository stores ingestion runs, immutable source
snapshots, canonical publications, canonical trials, and verified publication/trial links. A source
record with the same content hash is reused. A changed hash creates a new snapshot and updates the
canonical record's current snapshot pointer without deleting history.

Retrieval never writes extracted facts. Fact verification exposes independent `schema_valid`,
`source_span_verified`, and `human_reviewed` states; matching a number to a passage proves origin,
not interpretation correctness.

Derived artifacts are keyed by source text, parser/chunker configuration, embedding model revision,
dimension, normalization and metric. Any relevant change produces a new processing fingerprint and
an explicit rebuild reason. Unchanged source bytes alone are not sufficient to reuse an index.

The corpus cap applies to whole documents. Documents are considered in immutable seed-manifest
order; a document that would exceed 500 chunks is excluded as a whole and reported with a reason.
Articles are never silently truncated.

For multilingual E5, the 512-token maximum covers the complete formatted input: `passage:` prefix,
title, section label, passage text, and special tokens. A real E5 run must inject that model's exact
tokenizer with truncation disabled; the offline whitespace counter is only a deterministic boundary
fixture. An input that cannot fit is rejected or re-chunked, never silently truncated.

