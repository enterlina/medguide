from scripts.build_supplement_source_coverage import normalize, score_hit, source_kind


def test_normalize_separates_display_qualifiers() -> None:
    assert normalize("NAC (N-Acetylcysteine)") == "nac"
    assert normalize("Vitamin D3 + K2") == "vitamin d3 k2"


def test_score_hit_accepts_an_exact_synonym() -> None:
    source = {
        "groupName": "Vitamin B9 (5-Methyltetrahydrofolate)",
        "synonyms": ["methylfolate", "5-MTHF"],
    }
    assert score_hit("methylfolate", source) == 1.0


def test_source_kind_does_not_treat_product_label_as_interaction_authority() -> None:
    matches = [{"fact_sheets": []}]
    assert source_kind(matches, 42) == "dsld_product_label_only"
    assert source_kind(matches, 0) == "no_official_interaction_source_found"


def test_source_kind_prefers_ods_then_nccih() -> None:
    ods = [{"fact_sheets": [{"link": "https://ods.od.nih.gov/factsheets/VitaminD/"}]}]
    nccih = [{"fact_sheets": [{"link": "https://www.nccih.nih.gov/health/cranberry"}]}]
    assert source_kind(ods, 100) == "nih_ods"
    assert source_kind(nccih, 100) == "nccih"
