from scripts.promote_meps_interaction_corpus import merge_catalog


def test_curated_catalog_overrides_generated_candidate() -> None:
    generated = [{"ingredient_id": "ingredient:vitamin-k", "canonical_name": "vitamin k", "aliases": []}]
    curated = [{"ingredient_id": "ingredient:vitamin-k", "canonical_name": "vitamin k", "aliases": ["K2"], "ingredient_kind": "supplement"}]
    merged = merge_catalog(curated, generated)
    assert merged == curated
