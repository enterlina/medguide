# NFCorpus retrieval — uncertainty and paired analysis

- Evaluable queries: **323**
- Bootstrap resamples: **10,000**
- Intervals: query-level non-parametric bootstrap, 95% CI

## nDCG@10 with uncertainty

| Method | Mean | 95% CI | Latency p50 | Latency p95 |
|---|---:|---:|---:|---:|
| bm25 | 0.3088 | 0.2748–0.3433 | 6.87 ms | 17.31 ms |
| dense | 0.3355 | 0.3008–0.3700 | 92.67 ms | 165.73 ms |
| rrf | 0.3461 | 0.3113–0.3813 | 0.13 ms | 0.17 ms |
| reranked | 0.2507 | 0.2225–0.2793 | 33.75 ms | 94.97 ms |

## Paired comparisons

### rrf vs dense

- ndcg_at_10: Δ +0.0106; 95% CI -0.0032 to +0.0247; not distinguishable; bootstrap p=0.1298.
- recall_at_20: Δ +0.0065; 95% CI -0.0049 to +0.0175; not distinguishable; bootstrap p=0.2348.
- recall_at_50: Δ +0.0029; 95% CI -0.0071 to +0.0127; not distinguishable; bootstrap p=0.5730.

### rrf vs bm25

- ndcg_at_10: Δ +0.0373; 95% CI +0.0231 to +0.0513; distinguishable; bootstrap p=0.0000.
- recall_at_20: Δ +0.0207; 95% CI +0.0132 to +0.0286; distinguishable; bootstrap p=0.0000.
- recall_at_50: Δ +0.0363; 95% CI +0.0252 to +0.0483; distinguishable; bootstrap p=0.0000.

### reranked vs rrf

- ndcg_at_10: Δ -0.0954; 95% CI -0.1161 to -0.0755; distinguishable; bootstrap p=0.0000.
- recall_at_20: Δ +0.0000; 95% CI +0.0000 to +0.0000; not distinguishable; bootstrap p=1.0000.
- recall_at_50: Δ +0.0000; 95% CI +0.0000 to +0.0000; not distinguishable; bootstrap p=1.0000.

## Limits

- NFCorpus measures retrieval on an external benchmark; it does not validate MedGuide clinical claims.
- RRF latency above is fusion-only. End-to-end hybrid latency also includes BM25 and dense retrieval.
- The reranker result applies only to the tested model and configuration; it is not evidence that reranking generally fails.

