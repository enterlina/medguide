# MedGuide evaluation improvement report

This report applies the external review recommendations to the current measured artifacts. It does not promote AI-screened or exact-span-matched records to human-reviewed status.

## Executive result

MedGuide has strong source traceability but is not yet ready to claim broad interaction coverage or extractor accuracy. The next optimization target is interaction coverage and false reassurance, not another UI expansion.

### Interaction corpus

- Stored rules: **7,865**.
- Exact passage found in the stored source section: **7,864 (99.99%)**.
- Deduplicated rule signatures: **6,912**.
- Duplicate groups: **813**, containing **1,766** stored rules.
- Review status: **7,824 extracted**, **40 source-span verified**, **1 rejected**, **0 human-reviewed**.

Exact source matching validates provenance only. It does not validate entity mapping, interpretation, severity, applicability, or recommended action.

### Interaction safety audit

- Curated cases: **56**.
- Re-evaluated against the expanded corpus on **2026-10-30**; rule statuses were not changed.
- Cases supported by the resolver/API: **31/56 (55.4%)**.
- Finding recall among resolved must-detect cases: **8/30 (26.7%)**.
- False-reassurance proxy: **22/30 (73.3%)**.
- Resolved negative controls: **1**; abstention was correct for that one case. This sample is too small for a stable claim.
- Returned findings with a URL: **24/24**. URL presence is not citation precision.

Coverage increased because the expanded resolver recognizes more audit inputs. Conditional recall decreased because those newly resolved must-detect cases enlarged the denominator faster than the interaction corpus added matching findings. This is a more complete measurement, not evidence that previously returned findings disappeared.

The false-reassurance proxy remains the primary release blocker: a resolved must-detect case returned no finding. Unsupported entities are reported separately and never counted as safe or as correct abstention.

### Retrieval benchmark

NFCorpus contains **323 evaluable queries**. Query-level 10,000-sample bootstrap analysis found:

| Method | nDCG@10 | 95% CI |
|---|---:|---:|
| BM25 | 0.3088 | 0.2748–0.3433 |
| Dense E5 | 0.3355 | 0.3008–0.3700 |
| RRF | 0.3461 | 0.3113–0.3813 |
| Tested reranker | 0.2507 | 0.2225–0.2793 |

Paired bootstrap conclusions:

- RRF vs BM25: nDCG@10 Δ **+0.0373**, 95% CI **+0.0231 to +0.0513** — distinguishable.
- RRF vs Dense: nDCG@10 Δ **+0.0106**, 95% CI **−0.0032 to +0.0247** — not distinguishable.
- Tested reranker vs RRF: nDCG@10 Δ **−0.0954**, 95% CI **−0.1161 to −0.0755**. This rejects this configuration, not reranking in general.

## Changes made

1. Added a read-only full-corpus provenance and duplication audit.
2. Added query-level bootstrap confidence intervals, paired comparisons, and p50/p95 latency.
3. Added conditional safety metrics that separate unsupported coverage from resolved performance.
4. Added a deterministic 200-rule annotation sample and protocol. It does not pretend candidate-only annotation can measure recall.
5. Preserved `schema_valid`, source-span provenance, and human clinical review as separate concepts.

## Recommended order of work

1. Fix resolver/catalog coverage for the 25 unsupported safety cases.
2. Fix the 22 false-reassurance proxy cases and add regression tests for each.
3. Deduplicate at presentation and evaluation time; do not delete reviewed history.
4. Have two reviewers label at least 20% of the 200-rule sample and calculate agreement.
5. Add negative label passages to measure extractor recall and F1.
6. Build a MedGuide-specific retrieval qrels set; continue using NFCorpus/BioASQ only as external benchmarks.
7. Add citation-support judgments. Do not rename URL coverage as citation precision.

## Claims that remain unsupported

- Extractor precision, recall, and F1: no completed human gold set yet.
- Clinical correctness of all 7,864 exact-span matches: exact quotation is insufficient.
- Broad safety coverage: current curated-case coverage is 55.4%, with finding recall of only 26.7% among resolved must-detect cases.
- General reranker quality: only one tested reranker/configuration performed poorly.

