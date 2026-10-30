# FilmScope reuse audit

No FilmScope notebook, checkpoint, raw dataset, or lockfile was present in the inspected workspace.
The v1.2 specification's static audit is therefore the only available source. Historic metrics were
not reproduced or imported as MedGuide results.

Reimplemented patterns: full-hash artifact fingerprints, atomic JSON writes, E5-style interface
boundaries, exact normalized-vector reference search, BM25, chunk-level reciprocal-rank fusion, an
optional rerank stage, typed evaluation rows, and persisted run manifests.

Rejected patterns: document-level pre-deduplication, FilmScope title filters/router, character-only
chunks, same-set abstention calibration, mixed score semantics, regex-only judge validation, and
stale notebook outputs. No notebook code or side effects are imported at runtime.

