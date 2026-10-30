# Interaction corpus provenance audit

This audit is read-only and covers every stored rule.

- Rules: **7,865**
- Exact stored-source span matches: **7,864** (100.0%)
- Source span mismatches: **1**
- Deduplicated signatures: **6,912**
- Duplicate groups: **813**
- Rules in duplicate groups: **1,766**

## Critical interpretation

source_span_exact_match verifies provenance only. It does not verify clinical interpretation and does not promote source_span_verified or human_reviewed status.

Exact matching demonstrates that the quoted text came from the stored label. It does not demonstrate that the extractor interpreted the passage correctly.

