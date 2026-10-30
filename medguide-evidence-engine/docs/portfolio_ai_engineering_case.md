# MedGuide Evidence Engine — AI Engineering Portfolio Case

**Measured status: 2026-10-30.** This document describes a research prototype, not a clinically
validated decision-support system.

- **Live demo:** https://medguidenxt.com/interactions
- **Devpost:** https://devpost.com/software/medguide-ai-medication-supplement-intelligence
- **Demo video:** https://youtu.be/zyctKYUrL9U?si=583ddMtDRrbLeXQB
- **Source code:** https://github.com/enterlina/medguide

## Executive summary

MedGuide is an evidence-grounded assistant for people who want to understand how medicines,
supplements, foods, and drinks may interact and what scientific studies say about a selected
ingredient. The product combines two user journeys:

1. **Taking & Combining** — practical instructions and interaction findings linked to official
   FDA, DailyMed, and NIH sources.
2. **What Studies Say** — a structured view of PubMed studies, study design, participants,
   results, relevance, and journal-level metadata.

The central engineering constraint is safety: missing evidence must never be presented as proof
of safety, registrations must not be treated as positive trial results, and machine-extracted
rules must remain visibly separate from expert-reviewed rules.

## 1. Problem and product goal

Medication information is fragmented across product labels, scientific publications, trial
registries, and supplement fact sheets. The original product prototype displayed long source
passages, but users had difficulty answering basic questions quickly:

- Can these items be taken together?
- Should doses be separated?
- Does food or a drink affect the medicine?
- What does the evidence actually say about this supplement?
- Is the evidence direct, indirect, or still unverified?

The project goal was to build a traceable retrieval and evidence platform rather than a general
chatbot. Every user-facing claim must preserve its source URL and exact source passage.

## 2. Data sources

### Official label and safety sources

- **DailyMed SPL XML** — exact product labels, sections, version information, and source text.
- **openFDA Drug Label API** — FDA label fields such as interactions, contraindications,
  warnings, dosage, patient information, and use in specific populations.
- **NIH Office of Dietary Supplements** — professional fact sheets for vitamins and minerals.
- **RxNorm** — normalization of brands and generic names; not used as an interaction database.

### Research sources

- **PubMed / PMC** — titles, abstracts, publication metadata, study types, funding and conflict
  disclosures when reported.
- **ClinicalTrials.gov** — trial registrations, kept distinct from publications and results.
- **OpenAlex** — citation counts and open journal metrics with retrieval dates.

### External evaluation datasets

- **NFCorpus** — 3,633 biomedical documents and 323 test questions with relevance judgments.
- **BioASQ 14B pilot** — biomedical questions with gold PubMed identifiers.

## 3. Corpus construction

The reproducible ingestion flow is:

`Download → Parse → Normalize → Extract → Validate → Store → Index`

### 3.1 Normalization

Products and active ingredients are separate entities. A product such as Excedrin Migraine is
resolved to acetaminophen, aspirin, and caffeine. Exact DailyMed SETIDs are retained so the
system can link the product to its own label rather than an arbitrary label for the same generic
ingredient.

The current pharmacy-product expansion contains:

- 500 exact DailyMed product entries: 200 OTC and 300 prescription products;
- 497 automatically mapped products;
- 3 intentionally unresolved products requiring manual ingredient mapping;
- 601 normalized ingredient records after merging with the existing catalog;
- 768 stored official or regulatory documents.

The product list proves that a DailyMed label exists; it does not prove current retail
availability or popularity.

### 3.2 Interaction extraction

The rule extractor is deliberately conservative. It scans relevant official-label sections,
retains exact source passages, and emits typed candidates for:

- drug–drug;
- drug–supplement;
- drug–food;
- drug–beverage;
- timing separation;
- contraindications;
- population-specific warnings.

Each rule has an independent validation state:

`extracted → source_span_verified → human_reviewed`

The current database contains 7,865 stored rules: 7,824 extracted candidates, 40
source-span-verified rules, 1 rejected rule, and 0 human-reviewed rules. A read-only provenance
audit found the exact saved passage in the corresponding stored source section for 7,864 rules
(99.99%). This verifies source fidelity only; it does not validate entity mapping, severity,
applicability, interpretation, or recommended action. The audit also found 6,912 unique rule
signatures and 813 duplicate groups containing 1,766 stored rules.

### 3.3 Research discovery

PubMed discovery is performed by normalized ingredient, not by arbitrary brand text. Searches are
bounded by year and result count, stored as a separate candidate layer, and can be screened by an
LLM before human review. For the first pharmacy-product batch, 20 new ingredients were searched
across 2022–2026, producing 84 unique publication candidates with zero search errors. Two
ingredients had no result in that bounded search. This is bounded discovery, not evidence coverage
of the complete 601-ingredient catalog.

## 4. Chunking and embeddings

Documents are split into traceable chunks that preserve document ID, section, source type, and
source URL. The full E5 input budget includes the prefix, title, section, text, and special tokens;
silent truncation is not allowed.

Dense retrieval uses `intfloat/multilingual-e5-base` with 768-dimensional normalized embeddings.
Documents and queries use the same model and normalization strategy. Embeddings and model metadata
are persisted so experiments are reproducible.

## 5. Retrieval architecture

The retrieval experiment compares three paths:

1. **BM25 top-20** for exact terms, identifiers, and lexical matches.
2. **Dense top-20** for semantic similarity.
3. **Hybrid**: BM25 top-20 + Dense top-20 → Reciprocal Rank Fusion → top-20.

The architecture intentionally separates retrieval relevance from evidence applicability. A study
about a related magnesium form can be topically relevant without being direct evidence for
magnesium glycinate. Population, form, dose, outcome, study quality, evidence direction, and
citation support are evaluated after broad retrieval.

## 6. Retrieval evaluation

### NFCorpus

| Method | nDCG@10 | MRR@10 | Recall@20 | Hit@10 |
| --- | ---: | ---: | ---: | ---: |
| BM25 | 0.3088 | 0.5199 | 0.1792 | 0.6873 |
| Dense E5 | 0.3355 | 0.5338 | 0.1934 | 0.7059 |
| Hybrid RRF | **0.3461** | **0.5535** | **0.1999** | **0.7307** |
| Experimental reranker | 0.2507 | 0.4187 | 0.1999 | 0.6780 |

RRF reached nDCG@10 0.3461 (95% bootstrap CI 0.3113–0.3813). It outperformed BM25 by
0.0373 (95% CI 0.0231–0.0513). Its 0.0106 advantage over Dense E5 was not statistically
distinguishable from zero (95% CI −0.0032–0.0247; bootstrap two-sided p ≈ 0.13). The tested
reranker configuration reduced top-rank quality; this rejects that checkpoint and candidate-pool
configuration, not reranking in general.

### BioASQ restricted-corpus pilot

| Method | nDCG@10 | MRR@10 | Recall@20 | Hit@10 |
| --- | ---: | ---: | ---: | ---: |
| BM25 | 0.7492 | 0.8449 | 0.7931 | 0.9700 |
| Dense E5 | 0.7404 | 0.8442 | 0.7567 | 0.9500 |
| Hybrid RRF | **0.7797** | **0.8519** | **0.8280** | **0.9700** |

This is a 200-question pooled-gold experiment over a restricted PubMed corpus, not the official
full-PubMed BioASQ leaderboard benchmark. These external benchmarks validate retrieval mechanics;
they do not replace relevance judgments for MedGuide’s own medication and supplement questions.

## 7. Interaction safety evaluation

The current curated benchmark contains 56 cases. The resolver supports 31/56 cases (55.4%). Among
30 resolved must-detect cases, the API returned a finding for 8 (26.7%). The resulting
false-reassurance proxy is 22/30 (73.3%): a resolved must-detect case returned no finding. This is
a release-blocking diagnostic, not a clinically adjudicated population estimate.

All 24 returned findings contained a source URL. URL presence is not citation precision; citation
precision requires a human judgment that the passage supports the displayed claim. Only one
resolved negative control is currently available, so no stable abstention-accuracy claim is made.

## 8. Answer generation and citation safety

The generator receives only the selected source fragments within an explicit context budget. The
exact fragments sent to the model are stored. Generated answers must distinguish:

- `schema_valid` — the output follows the required structure;
- `source_span_verified` — the cited text exists in the stored source;
- `human_reviewed` — a qualified reviewer approved the interpretation.

A matching number or quotation proves provenance, not correct medical interpretation. This is why
clinical review remains a separate workflow with reviewer identity, comments, optimistic locking,
and an immutable audit trail.

## 9. System architecture

### Backend

- FastAPI application;
- Pydantic domain models and strict validation;
- SQLite for the local MVP, with repository boundaries that allow later migration;
- source-specific adapters for DailyMed, openFDA, NIH ODS, RxNorm, PubMed, and registries;
- persistent retrieval artifacts and experiment reports.

### Frontend

- Next.js application;
- **Taking & Combining** for products, ingredients, food, drinks, timing, and interactions;
- **What Studies Say** for structured scientific evidence;
- dynamic autosuggest sourced from canonical names, aliases, and exact pharmacy products;
- source links and expandable original passages;
- pinned selections persisted locally.

### Security and operational boundaries

- provider keys remain backend-only;
- ingestion and indexing endpoints are not public;
- no automatic bulk clinical approval;
- absence of a rule is reported as incomplete coverage, not “safe.”

## 10. Testing and reproducibility

The current automated suite contains 94 passing Python tests. Ruff, ESLint, and TypeScript checks
pass locally. The tests cover source adapters, interaction extraction, review transitions, corpus
audits, retrieval evaluation, and API behavior; the number of tests is not presented as a quality
metric by itself. Retrieval notebooks preserve their outputs, and machine-generated screening
results are stored separately from human annotations.

Important reproducibility artifacts include:

- `notebooks/retrieval_experiment_results.ipynb`;
- `notebooks/nfcorpus_benchmark_results.ipynb`;
- `artifacts/external-benchmarks/`;
- `artifacts/retrieval-experiment/`;
- `artifacts/interactions/pharmacy_product_ingestion/`;
- `data/products/us_pharmacy_500/`.

## 11. Engineering decisions and lessons

1. **Broad retrieval before strict PICO filtering.** Early strict filters can remove useful indirect
   evidence. Applicability is evaluated after retrieval.
2. **Retrieval conclusions require uncertainty estimates.** RRF beat BM25 on NFCorpus, but its
   measured advantage over Dense E5 was not statistically distinguishable.
3. **A reranker is not automatically an improvement.** The tested checkpoint over a fixed top-20
   candidate pool harmed nDCG and MRR; this does not generalize to every reranker.
4. **Unknown is not negative.** Missing participant counts, disclosures, or relevance labels remain
   “not reported” or “not reviewed.”
5. **Source fidelity and interpretation are different checks.** Exact-span verification cannot
   substitute for clinical review.
6. **Product and ingredient identities must be separate.** This prevents combination brands and
   formulation-specific labels from being flattened incorrectly.

## 12. Current limitations

- Most extracted interaction rules still require source-span and clinical review.
- Current resolver coverage is 55.4% on the curated safety set, and the finding-recall proxy is
  26.7% among resolved must-detect cases.
- Extractor precision, recall, and F1 are not yet available because the human gold set is not
  complete.
- The 497/500 automatic product mappings have not yet received a sampled human accuracy audit.
- PubMed candidates found by automated discovery are not automatically direct evidence.
- Participant counts and study outcomes are incomplete when they cannot be reliably extracted from
  the available abstract.
- Journal metrics are contextual signals, not measures of whether an individual claim is true.
- The local SQLite deployment is appropriate for the prototype but not the final multi-user review
  system.

## 13. Next steps

1. Fix unsupported resolver cases and add regression tests for the 22 false-reassurance cases.
2. Complete the extractor gold set and report precision, recall, and F1 by interaction type.
3. Review the three unresolved pharmacy products and audit a random sample of automatic mappings.
4. Complete topic-relevance judgments for MedGuide questions and report Topic Recall@20/50 and
   Topic nDCG@10.
5. Add citation-support judgments and a larger negative-control set for abstention evaluation.
6. Continue bounded PubMed discovery for the remaining normalized pharmacy ingredients.
7. Migrate the review store to PostgreSQL and add production authentication before public clinical
   review.

## Portfolio statement

This project demonstrates end-to-end AI engineering: heterogeneous data ingestion, entity
normalization, evidence-preserving extraction, hybrid information retrieval, statistically tested
retrieval comparisons, RAG answer constraints, human-in-the-loop validation, full-stack product
design, and explicit safety boundaries. The strongest result is not a single model score; it is a
system that makes uncertainty, provenance, failure modes, and review status visible and testable.
