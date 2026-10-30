# MedGuide Interaction Audit v1

- Executed: 2026-10-30T01:57:57.802834+00:00
- Endpoint: `http://127.0.0.1:3000/api/interactions/check`
- Fixture: `interaction_gold_v1` (56 cases)
- Resolver inventory: 100 names; 74 resolved, 26 unsupported, 0 errors
- App commit: `unavailable`
- Safety note: review-required rows are provisional; missing edges never prove safety.

## Overall results

- PASS: 2
- PARTIAL: 4
- FAIL: 4
- UNSUPPORTED: 25
- ERROR: 0
- NEEDS_HUMAN_REVIEW: 21

## Results by category

| Category | Total | PASS | PARTIAL | FAIL | UNSUPPORTED | ERROR | NEEDS_HUMAN_REVIEW |
|---|---:|---:|---:|---:|---:|---:|---:|
| drug_drug | 15 | 0 | 0 | 0 | 2 | 0 | 13 |
| drug_food | 7 | 1 | 0 | 0 | 4 | 0 | 2 |
| drug_supplement | 18 | 1 | 3 | 4 | 9 | 0 | 1 |
| drug_timing | 7 | 0 | 1 | 0 | 6 | 0 | 0 |
| negative_control | 9 | 0 | 0 | 0 | 4 | 0 | 5 |

## Highest-priority gaps

- **MG009** (UNSUPPORTED): Unresolved inputs: clarithromycin Source: https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=9f89e53e-a8fb-4ba7-a26d-21a962abcb1b&type=display
- **MG017** (UNSUPPORTED): Unresolved inputs: spinach/kale Source: https://health.ucsd.edu/for-health-care-professionals/anticoagulation-guidelines/warfarin/supplement-interactions/
- **MG018** (UNSUPPORTED): Unresolved inputs: St. John's wort Source: https://health.ucsd.edu/for-health-care-professionals/anticoagulation-guidelines/warfarin/supplement-interactions/
- **MG019** (UNSUPPORTED): Unresolved inputs: CoQ10 Source: https://health.ucsd.edu/for-health-care-professionals/anticoagulation-guidelines/warfarin/supplement-interactions/
- **MG020** (UNSUPPORTED): Unresolved inputs: St. John's wort Source: https://www.nccih.nih.gov/health/providers/digest/how-medications-and-supplements-can-interact-science
- **MG021** (UNSUPPORTED): Unresolved inputs: oral contraceptive, St. John's wort Source: https://www.nccih.nih.gov/health/providers/digest/how-medications-and-supplements-can-interact-science
- **MG030** (FAIL): Expected relationship was not returned by any reviewed, preliminary, or label-mention bucket. Source: https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=237cc591-c40b-416f-ac00-96cd61bc59dc
- **MG031** (UNSUPPORTED): Unresolved inputs: zinc supplement Source: https://medlineplus.gov/druginfo/meds/a688016.html
- **MG032** (FAIL): Expected relationship was not returned by any reviewed, preliminary, or label-mention bucket. Source: https://medlineplus.gov/druginfo/meds/a688016.html
- **MG033** (FAIL): Expected relationship was not returned by any reviewed, preliminary, or label-mention bucket. Source: https://www.medlineplus.gov/druginfo/meds/a682063.html

## Interpretation limits

- PASS is only available for deterministic checks against verified-anchor rows.
- NEEDS_HUMAN_REVIEW is intentionally not counted as PASS or FAIL.
- Schedule context is not accepted by the current public API and is reported as unsupported when no pair-level rule exists.
- The runner performs no medication changes and sends only synthetic fixture data.
