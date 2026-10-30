# Supplement discovery corpus — 27 October 2026

## Scope

- Catalog: 100 trending supplement ingredients, forms, and product concepts supplied for MedGuide.
- Source: PubMed E-utilities only in this discovery pass.
- Publication window: 1 January 2021 through 27 October 2026.
- Selection: human records indexed as Clinical Trial, Randomized Controlled Trial, Systematic
  Review, or Meta-Analysis.
- Per-supplement cap: three most recent PubMed records.
- Corpus cap: 500 source documents; no document was silently truncated.

## Result

- 240 supplement-to-publication associations.
- 220 unique PubMed publications after PMID deduplication.
- 220/220 records contain abstracts and publication, indexing, source-update, and check metadata.
- 16 catalog entries returned no records under the strict query and are retained as discovery gaps.
- Every record remains `admitted_to_evidence=false`, `source_span_verified=false`, and
  `human_reviewed=false`.

The corpus is a candidate set, not an efficacy result. Query matching can still produce records
whose intervention, population, or outcome is not applicable to the promoted use. PICO screening,
fact extraction, deduplication by trial family, and human review are required before a record can
affect a product card or MedIndex.

## Strict-query gaps

1. Apigenin
2. Glycine
3. Apple Cider Vinegar Gummies
4. Creatine Gummies
5. Clear Whey Protein
6. Beetroot Nitrates
7. Electrolyte Powders
8. Marine Collagen
9. Ceramide Supplements
10. Biotin Gummies
11. Silica Supplements
12. Menopause Probiotic Blends
13. Vitamin D3 + K2
14. Quercetin + Bromelain
15. Ergothioneine
16. Fadogia Agrestis

A gap means that the exact catalog query returned no eligible recent PubMed record. It does not
prove absence of research. Product-format gaps should be followed by ingredient-level searches,
while preserving the distinction between direct and indirect evidence.

## Generated artifacts

- `data/supplements/discovery/manifest.json`: reproducible selection rules and counts.
- `data/supplements/discovery/pubmed_recent.json`: deduplicated publication metadata and abstracts.
- `data/supplements/discovery/supplement_publication_links.json`: query-level supplement mappings.
- `data/supplements/discovery/evidence_gaps.json`: zero-result queries for follow-up.

## Required next processing stage

1. Resolve each candidate to canonical ingredient, form, and product entities.
2. Screen human population, intervention/form, comparator, outcome, and promoted-use applicability.
3. Link registrations and publications into trial families to prevent double counting.
4. Extract structured facts with explicit missingness states.
5. Verify extracted source spans and numerical values.
6. Review eligible records before admitting them to evidence.
7. Build section-aware chunks and embeddings only from the screened corpus.

