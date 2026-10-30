# MedGuide US Popularity Enrichment and PubMed Discovery

Generated: 2026-10-29

## Outcome

- Catalog entities evaluated: **125**.
- MEPS 2024 medications matched: **21**.
- NHANES 2021–2023 supplements matched: **72**.
- Existing entities with publication links before this run: **84**.
- Additional entities searched in PubMed: **41**.
- New entity-publication links: **75**.
- Unique recent PubMed publications retrieved: **71**.
- Entities with no result under the bounded query: **16**.
- NCBI request errors after retry: **0**.

## Official sources

- MEPS HC-254A 2024 Prescribed Medicines File: https://meps.ahrq.gov/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-254A
- NHANES August 2021–August 2023 DSQIDS_L: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DSQIDS_L.htm
- PubMed discovery: NCBI E-utilities, human clinical trials, randomized trials, systematic reviews and meta-analyses published from 2021-01-01 through 2026-10-29.

## Ranking definitions

The system does **not** combine prescription drugs and supplements into one score.

- MEPS rank is calculated within matched MedGuide medications. Each person is counted once per matched medication, using `PERWT24F`.
- NHANES rank is calculated within matched MedGuide supplements. Each participant is counted once per matched supplement, using `WTDRD1`.
- Standard nutrients can use an explicitly flagged nutrient proxy. Combination products and special delivery forms do not inherit a single-nutrient estimate.
- `not_matched` means no defensible automatic match was found. It does not mean the product is unpopular or unused.
- Estimates are survey-weighted values, not sales figures, prescribing recommendations, or evidence of effectiveness.

## Highest-ranked matched medications

| Rank | Medication | Weighted estimated users | Unweighted people |
|---:|---|---:|---:|
| 1 | Atorvastatin | 29,693,563 | 2,163 |
| 2 | Amoxicillin | 25,867,481 | 1,423 |
| 3 | Metformin | 19,618,344 | 1,332 |
| 4 | Amlodipine | 19,058,016 | 1,402 |
| 5 | Levothyroxine | 18,951,597 | 1,289 |
| 6 | Lisinopril | 18,884,866 | 1,369 |
| 7 | Losartan | 17,250,382 | 1,202 |
| 8 | Acetaminophen | 13,742,463 | 909 |
| 9 | Omeprazole | 13,105,287 | 915 |
| 10 | Gabapentin | 11,481,839 | 842 |

## Highest-ranked matched supplements

| Rank | Supplement | Weighted estimated 30-day users | Unweighted participants |
|---:|---|---:|---:|
| 1 | Vitamin D | 136,980,307 | 3,017 |
| 2 | Calcium | 113,355,299 | 2,428 |
| 3 | Magnesium | 72,862,019 | 1,618 |
| 4 | Iron | 48,370,359 | 1,052 |
| 5 | Vitamin D3 + K2 | 19,905,848 | 464 |
| 6 | Menopause Probiotic Blends | 15,023,605 | 319 |
| 7 | Choline | 14,158,569 | 290 |
| 8 | Biotin Gummies | 10,898,868 | 256 |
| 9 | Melatonin | 6,823,185 | 144 |
| 10 | Ashwagandha (KSM-66) | 3,122,159 | 44 |

## PubMed gaps from the bounded search

No eligible recent result was returned for: Apigenin, Glycine, Apple Cider Vinegar Gummies, Creatine Gummies, Clear Whey Protein, Beetroot Nitrates, Electrolyte Powders, Marine Collagen, Ceramide Supplements, Biotin Gummies, Silica Supplements, Menopause Probiotic Blends, Vitamin D3 + K2, Quercetin + Bromelain, Ergothioneine, and Fadogia Agrestis.

This is a query result, not proof that no research exists. The next review should broaden synonyms, separate combination products into ingredients, and inspect older or non-indexed evidence without silently changing the production corpus.
