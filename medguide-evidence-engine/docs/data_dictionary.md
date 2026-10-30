# M1 data dictionary

- `ingestion_runs`: source, query, requested cap, status, timestamps, counts, and errors.
- `source_snapshots`: immutable source/external-ID/version records with content hash, retrieval time,
  source update time, license, raw location, parser version, fetch status, and supersession pointer.
- `publications`: canonical publication identity using PMID, PMCID, and DOI.
- `clinical_trials`: canonical trial identity using NCT ID, with registration/result/publication
  states stored separately.
- `publication_trial_links`: verified identifier relationships; links do not merge the two entities.
- `source_document_id`: common retrieval identity for publication, PMC, and registry documents.
- `trial_family_id`: separate grouping identity used to prevent publication/registry double counting.
- fact verification: independent `schema_valid`, `source_span_verified`, and `human_reviewed` flags.

## Supplement catalog

- `Ingredient`: canonical name, synonyms, scientific search terms, and studied forms.
- `SupplementProduct`: market-specific product and its ingredient/form/amount composition.
- A product-to-ingredient link supports discovery; it does not establish formulation or dose
  equivalence with a study intervention.

## Structured evidence

- `StructuredEvidenceRecord`: source identity, ingredient/product links, research question, PICO,
  sample size, intervention dose/frequency, duration, outcomes, results, adverse events,
  limitations, funding, sponsor, manufacturer involvement, risk of bias, and freshness metadata.
- `EvidenceValue.state`: one of `reported`, `not_reported`, `not_extracted`, or `not_applicable`.
  These states are never collapsed into null or interpreted as equivalent.
- `ManufacturerInvolvement`: separate fields for company funding, supplied product, manufacturer
  employee participation, author financial relationships, and documented independence.
- `admitted_to_evidence=true` requires schema validation, source-span verification, and human review.

## Retrieval and freshness

- `ScientificSection`: abstract, methods, participants, intervention, results, adverse events,
  limitations, or funding/conflicts.
- `EvidenceChunkMetadata`: evidence-record link, ingredient IDs, section, PICO terms, and processing
  fingerprint. Similarity scores are retrieval signals, not quality judgments.
- `FreshnessMetadata`: distinct publication, indexing, source-update, and last-check timestamps plus
  the evidence version used by downstream conclusions.

