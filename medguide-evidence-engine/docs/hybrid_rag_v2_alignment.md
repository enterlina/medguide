# Hybrid RAG v2 alignment review

## Implemented locally

### Knowledge base

- Curated PubMed discovery corpus for 100 supplements, bounded to three recent eligible records per
  supplement and 500 chunks overall.
- PMID deduplication, immutable content hashes, source/check timestamps, evidence version, and
  explicit discovery gaps.
- Publication correction/retraction relationships and derived integrity status are retained.
- Abstracts are represented only as `Abstract` sections; they are never presented as full text.
- Section-aware document and chunk contracts already support Methods, Participants, Intervention,
  Results, Adverse Events, Limitations, and Funding/Conflicts when licensed full text is available.
- New records remain unreviewed candidates and cannot affect evidence conclusions or MedIndex.

### Retrieval

- Dense top-20 plus BM25 top-20.
- Reciprocal Rank Fusion by chunk identity.
- Top-20 reranking followed by a top-5 complete-context budget.
- Metadata filters and per-document caps.
- Full E5 input budgeting includes prefix, title, section, passage, and special tokens; silent
  truncation is forbidden.
- Whole documents are excluded and reported if adding them would exceed the 500-chunk cap.

The offline reranker is deterministic lexical overlap plus RRF. A validated cross-encoder or hosted
reranker remains a production enhancement and must be evaluated before replacement.

### Evaluation

- The original 400 questions remain a broad coverage dataset.
- `golden_question_candidates_2000.json` contains 20 queries for each of all 100 catalog
  supplements, including effectiveness, RCTs, reviews, dose, duration, safety, interactions,
  population, long-term evidence, null results, formulation, comparison, funding, and multi-study
  synthesis.
- 10% of the 2,000 v2 queries are multilingual and 10% contain typos/colloquial wording.
- Ambiguous queries carry explicit selected-product context.
- Candidate PMIDs are discovery aids only. Expected PMIDs, graded relevance, and expected answer
  states remain empty until human review.
- Evaluation code supports Recall@5, Recall@10, nDCG@10, MRR, complete-evidence coverage, and gap
  abstention.

### Freshness and appraisal contracts

- Publication, indexing, source-update, and last-check timestamps are separate.
- Structured evidence supports PICO, dose, duration, results, adverse events, limitations, funding,
  sponsor, manufacturer involvement, and risk of bias.
- `reported`, `not_reported`, `not_extracted`, and `not_applicable` are distinct states.
- Retracted publications cannot be admitted to evidence.
- Evidence admission requires schema validation, source-span verification, and human review.

## Still required before production claims

1. Human reviewers must screen candidate PMIDs and assign graded relevance and reference facts for
   the 2,000 Golden Dataset candidates.
2. ClinicalTrials.gov discovery and publication-to-registration trial-family linking must be
   expanded beyond the magnesium fixture.
3. Licensed PMC full-text acquisition must enforce article-level reuse rights and preserve raw files
   in document/object storage.
4. PICO extraction and source-span validation must run over the 220 candidate abstracts; discovery
   matches alone are not evidence.
5. Retraction/correction changes need scheduled incremental processing and downstream invalidation.
6. Daily jobs are designed but not provisioned; no scheduler or cloud infrastructure is claimed.
7. PostgreSQL/pgvector and PostgreSQL full-text search remain a migration target. SQLite and local
   vector artifacts remain the bounded MVP implementation.

