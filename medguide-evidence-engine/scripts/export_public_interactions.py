"""Export the minimum interaction data required by the public Next.js UI.

The export intentionally excludes stored labels, review events, reviewer identities, and rejected
rules. It contains normalized lookup entries, display-ready label previews, public source URLs, and
the rule candidates that the existing public interaction engine is allowed to display.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.models import InteractionRule, ValidationStatus  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


ACTIONABLE = re.compile(
    r"\b(?:do not take|should not take|not take|avoid|contraindicat|monitor|"
    r"may increase|may decrease|might increase|might reduce|can reduce|interact with|"
    r"increases? (?:the )?risk|serious and potentially dangerous interaction|"
    r"not recommended|separate)\b",
    re.IGNORECASE,
)
NON_INTERACTION = re.compile(
    r"\b(?:no clinically significant interaction|no meaningful interaction|"
    r"did not meaningfully alter|has no effect on the pharmacokinetics|"
    r"without clinically meaningful|low propensity for causing drug interactions)\b",
    re.IGNORECASE,
)


def resolution(item, *, resolution: str, product_ids=None, set_ids=None) -> dict:
    return {
        "ingredient_ids": item["ingredient_ids"],
        "canonical_names": item["canonical_names"],
        "rxcui": item.get("rxcui"),
        "resolution": resolution,
        "product_ids": product_ids or [],
        "product_set_ids": set_ids or [],
    }


def public_suggestion(value: str) -> bool:
    normalized = " ".join(value.split())
    return len(normalized) >= 2 and bool(re.search(r"[a-zA-Z]", normalized))


def build_export() -> dict:
    catalog = IngredientCatalog.from_json(
        ROOT / "data/products/us_pharmacy_500/active_ingredients.json",
        ROOT / "data/products/us_pharmacy_500/products.json",
    )
    repository = InteractionRepository(ROOT / "data/interactions/interactions.sqlite3")
    covered = repository.covered_ingredients()

    ingredient_aliases: dict[str, dict] = {}
    suggestions: set[str] = set()
    for ingredient in catalog.ingredients.values():
        if ingredient.ingredient_id not in covered:
            continue
        base = {
            "ingredient_ids": [ingredient.ingredient_id],
            "canonical_names": [ingredient.canonical_name],
            "rxcui": ingredient.rxcui,
        }
        for name in [ingredient.canonical_name, *ingredient.aliases]:
            if public_suggestion(name):
                ingredient_aliases[catalog.normalize(name)] = resolution(
                    base, resolution="pilot_catalog_exact"
                )
                suggestions.add(" ".join(name.split()))

    product_aliases: dict[str, dict] = {}
    for normalized, products in catalog._product_aliases.items():
        ingredient_ids = list(
            dict.fromkeys(
                ingredient_id
                for product in products
                for ingredient_id in product["ingredient_ids"]
                if ingredient_id in covered
            )
        )
        if not ingredient_ids:
            continue
        product_aliases[normalized] = resolution(
            {
                "ingredient_ids": ingredient_ids,
                "canonical_names": [catalog.ingredients[item].canonical_name for item in ingredient_ids],
            },
            resolution="pharmacy_product_exact",
            product_ids=[product["product_id"] for product in products],
            set_ids=[product["set_id"] for product in products],
        )
        for product in products:
            suggestions.update(
                " ".join(name.split())
                for name in product.get("search_aliases", [])
                if public_suggestion(name)
            )

    with repository.connect() as connection:
        rows = connection.execute(
            """SELECT r.payload_json, l.source_url, l.set_id
            FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
            WHERE r.validation_status != 'rejected'"""
        ).fetchall()

    rules = []
    for row in rows:
        rule = InteractionRule.model_validate_json(row["payload_json"])
        if rule.validation_status == ValidationStatus.EXTRACTED:
            if not ACTIONABLE.search(rule.source_passage.text):
                continue
            if NON_INTERACTION.search(rule.source_passage.text):
                continue
        payload = rule.model_dump(mode="json")
        payload["source_passage"]["readable_url"] = (
            f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={row['set_id']}"
            if row["set_id"]
            else row["source_url"]
        )
        rules.append(payload)

    guidance: dict[str, list[dict]] = {}
    for ingredient_id in sorted(covered):
        items = repository.label_guidance([ingredient_id])
        if items:
            guidance[ingredient_id] = [item.model_dump(mode="json") for item in items]

    return {
        "schema_version": 1,
        "suggestions": sorted(suggestions, key=str.casefold),
        "ingredient_aliases": ingredient_aliases,
        "product_aliases": product_aliases,
        "covered_ingredients": sorted(covered),
        "rules": rules,
        "guidance": guidance,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT.parent / "data/public-interactions.json",
    )
    args = parser.parse_args()
    payload = build_export()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(
        f"Saved {len(payload['suggestions'])} suggestions, {len(payload['rules'])} rules, "
        f"and guidance for {len(payload['guidance'])} ingredients to {args.output}"
    )


if __name__ == "__main__":
    main()
