# Real retrieval and ranking experiment

Run ID: `1ca01cbd85edbb91`  
Corpus: 220 PubMed publications, exact-token re-chunked to 352 valid chunks  
Questions: 140 stratified candidates from `golden_question_candidates_2000.json`

## Models and indexes

- Dense model: `intfloat/multilingual-e5-base`
  revision `d128750597153bb5987e10b1c3493a34e5a4502a`.
- Dense dimension: 768; query and passage vectors are L2-normalized.
- E5 inputs use `query:` and `passage:` prefixes respectively.
- Largest complete E5 input: 512 tokens, including metadata and special tokens.
- Second-stage reranker: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
- Reranker method: independent multilingual bi-encoder cosine similarity. It is real model
  inference, but not a cross-encoder. Largest reranker input: 507 tokens.
- BM25 and dense indexes cover the same ordered chunk set.

The original 225-chunk artifact used a whitespace token approximation. Exact E5 tokenization found
123 unsplit abstract inputs above the 512-token limit. The experiment rebuilt the same 220-document
corpus into 352 chunks without truncation or publication expansion.

## Retrieval methods

1. BM25 top-20.
2. Dense E5 cosine top-20.
3. BM25 top-20 plus dense top-20, RRF fusion, top-20 candidate set, MiniLM reranking, and top-5
   context selection. The debug report retains reranked top-10 for inspection.

## Latency

| Stage | Mean | Median | P95 |
| --- | ---: | ---: | ---: |
| BM25 | 1.26 ms | 1.18 ms | 1.90 ms |
| Dense query embedding + search | 34.74 ms | 31.95 ms | 48.90 ms |
| RRF + second-stage reranking | 13.79 ms | 12.50 ms | 19.27 ms |

Hybrid end-to-end latency is approximately the sum of the three stages; the hybrid timing column
does not double-count BM25 or dense retrieval.

## Ranking differences

| Pair | Mean top-10 Jaccard overlap | Same top-1 |
| --- | ---: | ---: |
| BM25 vs Dense | 0.216 | 43.6% |
| BM25 vs Hybrid | 0.371 | 18.6% |
| Dense vs Hybrid | 0.438 | 22.1% |

Per-question top-1 agreement, overlap count, and documents unique to either method are stored under
`ranking_differences` in `ranking_results.json`.

## Diagnostic candidate-PMID proxy

The following is not a relevance metric. It only checks whether top-5 contains one of the PubMed
records originally discovered for that supplement:

| Method | Candidate PMID hit@5 | Questions with candidate PMIDs |
| --- | ---: | ---: |
| BM25 | 87.5% | 120 |
| Dense | 91.7% | 120 |
| Hybrid | 77.5% | 120 |

Twenty selected questions belong to supplements with no strict discovery candidates and are excluded
from this proxy. The lower hybrid proxy suggests that the current bi-encoder reranker can displace
ingredient-matched records. It must not be declared better than BM25 or dense before human relevance
annotation.

## Relevance evaluation

Evaluable questions: **0 of 140**.

Recall@5, Recall@10, nDCG@10, and MRR are reported as unavailable because every pooled result is
currently `not_reviewed`. An unreviewed result is never interpreted as irrelevant. A question becomes
evaluable only after all unique documents in its pooled top-10 results are labeled and at least one
positive relevance judgment exists.

## Error analysis and recommendations

1. Dense retrieval currently has the strongest candidate-PMID proxy, but this is not verified
   relevance and may reward the discovery query rather than the user intent.
2. BM25 and dense rankings have low overlap, confirming that both retrieve meaningfully different
   candidates and supporting hybrid fusion.
3. The current second-stage bi-encoder reranker is space-efficient and multilingual, but the proxy
   regression means it should be compared with a multilingual cross-encoder after disk capacity is
   available.
4. Human reviewers should start with a balanced subset across categories, intents, typo queries, and
   multilingual queries. Save labels with the HTML report and rerun
   `scripts/evaluate_retrieval_annotations.py`.
5. Candidate relevance should include ingredient/form, population, comparator, outcome, and study
   design—not topic similarity alone.
6. Do not tune models against the 140-question reviewed set without creating a separate held-out
   split.

