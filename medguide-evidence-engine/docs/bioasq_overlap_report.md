# BioASQ 14b overlap audit

BioASQ `training14b.json` was compared with the current MedGuide supplement corpus by exact PMID.
The registered source dataset remains outside the repository; the generated report stores only its
filename and SHA-256 digest for provenance.

## Result

| Measure | Count |
| --- | ---: |
| BioASQ questions | 5,729 |
| Unique BioASQ gold PMIDs | 58,048 |
| MedGuide corpus documents | 220 |
| Overlapping PMIDs | 0 |
| BioASQ questions with overlap | 0 |

The absence of overlap does **not** mean either dataset is invalid or that the MedGuide publications
were not analyzed. BioASQ covers broad biomedical expert questions accumulated across challenge
editions. The current MedGuide corpus is a narrow, recent supplement corpus.

BioASQ therefore cannot provide direct relevance labels for the existing 140 MedGuide experiment
questions. It can still be used as an external benchmark for the retrieval pipeline and as a schema
reference for `question -> gold PMID -> evidence snippet -> ideal answer`.

## Reproduce

Run from `medguide-evidence-engine`:

```bash
python scripts/build_bioasq_overlap.py \
  --bioasq /Users/elenadalbonidarocha/Documents/medguide/dataset/BioASQ-training14b/training14b.json
```

Output: `artifacts/external-benchmarks/bioasq14b_overlap.json`.
