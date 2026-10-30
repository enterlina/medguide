# MedGuide supplement source coverage

Generated from the 100-item supplement catalog and the official NIH DSLD API.

## Results

- Catalog entries checked: **100**
- Automatically matched to a DSLD ingredient group after normalization: **93**
- Entries linked to an NIH ODS fact sheet: **6**
- Entries linked to an NCCIH fact sheet: **6**
- Entries with DSLD product labels but no linked ODS/NCCIH interaction source: **85**
- Entries with no official interaction source found in this pass: **3**
- Entries still lacking a sufficiently close DSLD ingredient-group match: **7**
- API errors: **0**

`not_found` means that the normalized query did not produce a sufficiently close DSLD
ingredient-group match. It does not mean that no information exists. Seven such entries still
have product-label keyword matches, so product identity and ingredient identity must not be
treated as the same thing.

An ODS or NCCIH link can apply to a broader ingredient family rather than the exact commercial
form. For example, a magnesium fact sheet is relevant context for magnesium glycinate but does
not prove that every interaction, dose or effect transfers unchanged to the glycinate form.

## Source roles

| Source | Use in MedGuide | Must not be interpreted as |
| --- | --- | --- |
| NIH ODS Health Professional Fact Sheets | Nutrient reference intakes, upper limits, deficiency, excess, safety and medication interactions | Product-specific composition or proof that a supplement treats a condition |
| NIH DSLD | Product names, label ingredients, amount per serving, form, manufacturer claims, warnings and label images | Independent verification, FDA approval, effectiveness or complete interaction guidance |
| National Academies DRI | Primary RDA, AI, EAR and UL reference values | Individual treatment or dosing advice |
| USDA DRI Calculator | Age-, sex- and life-stage presentation of DRI values | A diagnosis or personalized prescription |
| DailyMed / FDA labeling | Exact drug-label warnings, contraindications, administration and interactions | A source for ordinary dietary supplements that do not have a drug label |
| Drugs@FDA | FDA approval status, approval history and approved labeling | Evidence that an ordinary dietary supplement is approved |
| Orange Book | Approved drug products and therapeutic-equivalence information | Supplement approval or a general interaction database |
| NDC Directory | Product identification and listing metadata | FDA approval; an NDC does not denote approval |
| USPSTF / professional guidelines | Population- and condition-specific recommendations | A universal rule for every user or product |
| FDA dietary-supplement resources / NDI notifications | Regulatory status, safety notices, warning letters and new-ingredient notifications | Premarket FDA approval of a supplement |

## Required ingestion order

1. Normalize the ingredient and its form separately from the commercial product.
2. Match the ingredient to DSLD groups and preserve aliases and group IDs.
3. Match commercial products to DSLD labels; preserve the exact label version and image.
4. Ingest ODS safety, upper-limit and medication-interaction sections when available.
5. Use DailyMed, openFDA, Drugs@FDA and Orange Book only when the item is regulated as a drug.
6. Store guideline recommendations separately from label interactions.
7. Retrieve publications and trials for effectiveness as a separate evidence layer.
8. Never convert missing data into a green “safe” result.

## Normalization completed

The normalization manifest separates active components from aliases, branded forms, routes and
delivery forms. Examples:

- `Vitamin D3 + K2` → `vitamin D3` + `vitamin K2`; relationship: combination
- `Quercetin + Bromelain` → `quercetin` + `bromelain`; relationship: combination
- `Ashwagandha (KSM-66)` → ingredient: `ashwagandha`; branded form: `KSM-66`
- `Biotin Gummies` → ingredient: `biotin`; delivery form: `gummy`
- `Liposomal Glutathione` → ingredient: `glutathione`; delivery form: `liposomal`
- `Hyaluronic Acid (oral)` → ingredient: `hyaluronic acid`; route: `oral`

The full mapping is stored in `data/supplements/supplement_normalization.json`.

## Source classes after normalization

### NIH ODS linked

- Ca-AKG (Calcium Alpha-Ketoglutarate) — broader calcium context; exact-form applicability must be reviewed
- Acetyl-L-Carnitine (ALCAR)
- Magnesium Glycinate — broader magnesium context
- Magnesium L-Threonate — broader magnesium context
- Vitamin D3 + K2 — evaluate each component separately
- Zinc Carnosine — broader zinc context

### NCCIH linked

- Green Tea EGCG Extract
- Vitex Agnus-Castus
- Cranberry PACs
- Milk Thistle (Silymarin)
- Curcumin Phytosome — broader turmeric/curcumin context
- Elderberry Extract

### No official interaction source found in this pass

- Clostridium butyricum
- PHGG (Partially Hydrolyzed Guar Gum)
- C15:0 (Pentadecanoic Acid)

These three entries may still have scientific publications or product labels elsewhere. They must
not receive generated interaction claims until a suitable source is admitted and reviewed.

The machine-readable results are stored in:

- `data/supplements/source_coverage/supplement_source_coverage_100.json`
- `data/supplements/source_coverage/supplement_source_coverage_100.csv`
