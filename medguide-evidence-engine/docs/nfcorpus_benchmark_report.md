# NFCorpus retrieval benchmark

The MedGuide retrieval pipeline was evaluated on the official NFCorpus test split: 323 queries,
3,633 documents and graded qrels. Documents were split into 4,240 exact-token-audited chunks;
silent E5 truncation was not allowed.

| Method | Recall@10 | Recall@20 | Recall@50 | Recall@100 | nDCG@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.1511 | 0.1792 | 0.2122 | 0.2439 | 0.3088 | 0.5199 |
| Dense E5 | 0.1604 | 0.1934 | 0.2457 | **0.2969** | 0.3355 | 0.5338 |
| Pure RRF, k=60 | **0.1685** | **0.1999** | **0.2486** | 0.2935 | **0.3461** | **0.5535** |
| RRF + bi-encoder reranking | 0.1338 | 0.1999 | 0.2486 | 0.2935 | 0.2507 | 0.4187 |

Pure document-level RRF is strongest at top-10 and is the provisional retrieval default pending
BioASQ validation. Dense E5 retains the best Recall@100. Cosine similarity from
`paraphrase-multilingual-MiniLM-L12-v2` materially damages the top-10 ordering and must remain a
separate failed experimental configuration, not the default.

These results validate the pipeline on an external nutrition/medical benchmark. They do not transfer
qrels to MedGuide's own questions or remove the need for product-, formulation-, population- and
outcome-specific human judgments.
