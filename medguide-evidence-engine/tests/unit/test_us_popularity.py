from scripts.build_us_popularity import normalize, nutrient_column, phrase_match


def test_normalize_preserves_ingredient_words() -> None:
    assert normalize("Calcium + Vitamin D") == "calcium vitamin d"


def test_phrase_match_uses_word_boundaries() -> None:
    assert phrase_match("nature made vitamin d3", ["vitamin d3"])[0]
    assert not phrase_match("ironman recovery", ["iron"])[0]


def test_combination_does_not_use_single_nutrient_proxy() -> None:
    assert nutrient_column(
        {
            "display_name": "Vitamin D3 + K2",
            "canonical_name": "Vitamin D3 + K2",
            "aliases": [],
            "components": ["Vitamin D3", "Vitamin K2"],
        }
    ) is None
