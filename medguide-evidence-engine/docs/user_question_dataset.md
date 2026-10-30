# User question evaluation dataset

`evaluation/data/user_questions_400.json` contains 400 English-language question hypotheses for
100 supplement candidates. Each supplement has four intents:

1. effectiveness;
2. evidence and study quality;
3. dose, population, and outcome;
4. safety, interactions, and comparison.

The dataset is an evaluation input, not a scientific source. It must never be indexed as evidence,
quoted as support for a medical claim, or used to infer popularity. Every question is explicitly
marked `query_origin=expert_curated_hypothesis` and `popularity_verified=false`.

## Intended use

- coverage analysis against the discovered supplement corpus;
- retrieval and insufficient-evidence tests;
- PICO and ingredient-resolution tests;
- safety escalation tests;
- creation of a smaller, manually reviewed benchmark with source-document relevance judgments.

The 400 questions do not yet contain relevance labels or reference answers. They are therefore not
valid inputs for document recall, MRR, factual correctness, or answer-quality scoring until a human
reviewer assigns expected evidence records and acceptable answer states.

## Golden Dataset candidate v2

`evaluation/data/golden_question_candidates_2000.json` covers all 100 supplements with 20 queries
each. It adds language, difficulty, challenge tags, selected-product
context for ambiguous questions, expected evidence fields, and candidate PMIDs from discovery.

The candidate PMIDs are not relevance judgments. `expected_pmids`, `relevance_labels`, and expected
answer states intentionally remain unjudged until manual review. After review, retrieval evaluation
uses Recall@5, Recall@10, nDCG@10, and MRR; answer evaluation should separately score factual
support, completeness, citation quality, and appropriate insufficient-evidence behavior.

