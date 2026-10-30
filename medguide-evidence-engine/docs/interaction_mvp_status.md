# Drug Interaction Engine MVP — implementation status

## Implemented

- Bounded catalog of 25 active ingredients and supplements.
- Normalized `Ingredient → LabelDocument → InteractionRule → SourcePassage` models.
- Exact local alias resolution and online RxNorm lookup.
- Bounded openFDA label ingestion with generic-name fallback.
- Bounded DailyMed metadata lookup, SPL ZIP download, and XML section parsing.
- Conservative explicit-co-mention extraction for drug, supplement, food, beverage, and timing candidates.
- Directional timing model; an interval is null unless explicitly stated in the source.
- SQLite persistence with versioned label identity and source passages.
- Pair checking, combination ingredient expansion, duplicate-ingredient detection, and coverage gaps.
- `POST /api/interactions/check`.
- Protected review queue, strict state transitions, optimistic status checks, and immutable audit events.

## Safety boundary

Automatically extracted rules have `validation_status=extracted`. The API reports an
`INSUFFICIENT_DATA` coverage gap until review is completed. It never returns `SAFE` merely
because a rule is absent. The current pilot corpus is not ready for clinical use.

The public interaction check returns only `human_reviewed` rules. Machine candidates and
source-span-only rules are excluded.

## Review workflow

Protected endpoints require `X-Admin-Token`:

- `GET /api/interactions/review?status=extracted`
- `POST /api/interactions/review/{interaction_id}`
- `GET /api/interactions/review/{interaction_id}/history`

Allowed transitions:

1. `extracted → source_span_verified` or `rejected`
2. `source_span_verified → human_reviewed` or `rejected`
3. `human_reviewed` and `rejected` are terminal

Source-span promotion checks that the exact passage still occurs in the stored label section.
Every transition requires an expected current status, reviewer identity, and note. The command
line equivalent is `scripts/review_interaction_rule.py`.

## Current bounded corpus

The first pilot run ingested one openFDA and one DailyMed label for each of five ingredients:
acetaminophen, ibuprofen, aspirin, naproxen, and metformin. Remaining catalog ingredients are
fixed but not yet ingested. Machine candidates require source-span and human review.

## Deferred

- Human annotation/review workflow and promotion to `source_span_verified`/`human_reviewed`.
- NIH ODS and DSLD adapters.
- Product-level NDC/strength/form/route reconciliation across labels.
- OCR and interaction UI.
- Optional patient-profile conditions.
