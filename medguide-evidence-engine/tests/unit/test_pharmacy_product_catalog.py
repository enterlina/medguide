from app.interactions.catalog import IngredientCatalog
from app.interactions.models import Ingredient
from scripts.build_pharmacy_product_catalog import active_names, build_catalog, parse_rows


def test_parse_exact_dailymed_product() -> None:
    text = "| OTC-001 | Tylenol | TYLENOL (ACETAMINOPHEN) TABLET | Nov 11, 2024 | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc) |"
    row = parse_rows(text)[0]
    assert row["set_id"] == "abc"
    assert row["label_type"] == "otc"


def test_extracts_combination_ingredients() -> None:
    assert active_names("EXCEDRIN (ACETAMINOPHEN, ASPIRIN, AND CAFFEINE) TABLET") == [
        "acetaminophen", "aspirin", "caffeine"
    ]


def test_ambiguous_family_is_not_used_as_exact_alias() -> None:
    text = "\n".join([
        "| OTC-001 | Brand | BRAND (ASPIRIN) TABLET | Jan 01, 2026 | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a) |",
        "| OTC-002 | Brand | BRAND PLUS (ASPIRIN AND CAFFEINE) TABLET | Jan 01, 2026 | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b) |",
    ])
    catalog = [
        {"ingredient_id": "ingredient:aspirin", "canonical_name": "aspirin", "aliases": []},
        {"ingredient_id": "ingredient:caffeine", "canonical_name": "caffeine", "aliases": []},
    ]
    result = build_catalog(text, catalog)
    assert all("Brand" not in row["search_aliases"] for row in result["products"])


def test_exact_product_resolves_all_active_ingredients() -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:a", canonical_name="a", aliases=[]),
            Ingredient(ingredient_id="ingredient:b", canonical_name="b", aliases=[]),
        ],
        [{
            "product_id": "OTC-001",
            "set_id": "set-1",
            "ingredient_ids": ["ingredient:a", "ingredient:b"],
            "search_aliases": ["Example Cold & Flu"],
        }],
    )
    resolved = catalog.resolve_local("Example Cold & Flu")
    assert resolved.ingredient_ids == ["ingredient:a", "ingredient:b"]
    assert resolved.product_set_ids == ["set-1"]
    assert resolved.resolution == "pharmacy_product_exact"
