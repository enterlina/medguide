from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


DEFAULT_SUPPLEMENTS = Path("data/supplements/supplements_2025_2026.tsv")
DEFAULT_NORMALIZATION = Path("data/supplements/supplement_normalization.json")
DEFAULT_INGREDIENTS = Path("data/interactions/pilot_ingredients.json")
DEFAULT_PHARMACY_INGREDIENTS = Path("data/products/us_pharmacy_500/active_ingredients.json")
DEFAULT_PHARMACY_PRODUCTS = Path("data/products/us_pharmacy_500/products.json")
DEFAULT_MEPS_PUBMED_CATALOG = Path("data/catalog/meps_500/pubmed_catalog.json")
DEFAULT_OUTPUT = Path("data/catalog/entities.json")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the MedGuide search catalog independently of evidence availability.")
    parser.add_argument("--supplements", type=Path, default=DEFAULT_SUPPLEMENTS)
    parser.add_argument("--normalization", type=Path, default=DEFAULT_NORMALIZATION)
    parser.add_argument("--ingredients", type=Path, default=DEFAULT_INGREDIENTS)
    parser.add_argument("--pharmacy-ingredients", type=Path, default=DEFAULT_PHARMACY_INGREDIENTS)
    parser.add_argument("--pharmacy-products", type=Path, default=DEFAULT_PHARMACY_PRODUCTS)
    parser.add_argument("--meps-pubmed-catalog", type=Path, default=DEFAULT_MEPS_PUBMED_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalization = json.loads(args.normalization.read_text(encoding="utf-8"))
    ingredient_rows = json.loads(args.ingredients.read_text(encoding="utf-8"))
    pharmacy_ingredients = json.loads(args.pharmacy_ingredients.read_text(encoding="utf-8"))
    pharmacy_products = json.loads(args.pharmacy_products.read_text(encoding="utf-8"))
    meps_entities = json.loads(args.meps_pubmed_catalog.read_text(encoding="utf-8"))
    entities: dict[str, dict] = {}

    product_ingredient_ids = {
        ingredient_id
        for product in pharmacy_products
        for ingredient_id in product.get("ingredient_ids", [])
    }
    product_aliases: dict[str, list[str]] = {ingredient_id: [] for ingredient_id in product_ingredient_ids}
    for product in pharmacy_products:
        ingredient_ids = product.get("ingredient_ids", [])
        if len(ingredient_ids) != 1:
            continue
        product_aliases.setdefault(ingredient_ids[0], []).extend(product.get("search_aliases", []))

    for row in ingredient_rows:
        canonical = row["canonical_name"]
        entity_type = "supplement" if row.get("ingredient_kind") == "supplement" else "medication"
        entities[row["ingredient_id"]] = {
            "entity_id": row["ingredient_id"],
            "canonical_name": canonical,
            "display_name": canonical.title(),
            "entity_type": entity_type,
            "aliases": unique(row.get("aliases", [])),
            "components": [canonical],
            "category": "Medication" if entity_type == "medication" else "Vitamin or mineral",
            "popularity_rank": None,
            "popularity_source": "interaction_pilot",
            "evidence_query": " OR ".join([canonical, *row.get("aliases", [])]),
        }

    for row in meps_entities:
        canonical = row["canonical_name"]
        entity_id = row["entity_id"]
        existing = entities.get(entity_id, {})
        aliases = unique([*existing.get("aliases", []), *row.get("aliases", [])])
        entities[entity_id] = {
            "entity_id": entity_id,
            "canonical_name": canonical,
            "display_name": row.get("display_name", canonical.title()),
            "entity_type": row.get("entity_type", "medication"),
            "aliases": aliases,
            "components": unique(row.get("components", [canonical])),
            "category": "Commonly used US medication or supplement",
            "popularity_rank": existing.get("popularity_rank"),
            "popularity_source": "meps_500",
            "evidence_query": row.get("evidence_query") or " OR ".join([canonical, *aliases]),
        }

    for row in pharmacy_ingredients:
        ingredient_id = row["ingredient_id"]
        if ingredient_id not in product_ingredient_ids:
            continue
        canonical = row["canonical_name"]
        existing = entities.get(ingredient_id, {})
        aliases = unique([
            *existing.get("aliases", []),
            *row.get("aliases", []),
            *product_aliases.get(ingredient_id, []),
        ])
        # Product titles are useful for autosuggest, but PubMed queries should use
        # the active ingredient and concise aliases rather than dosage-form text.
        evidence_terms = unique([canonical, *row.get("aliases", [])])
        entities[ingredient_id] = {
            "entity_id": ingredient_id,
            "canonical_name": canonical,
            "display_name": canonical.title(),
            "entity_type": "supplement" if row.get("ingredient_kind") == "supplement" else "medication",
            "aliases": aliases,
            "components": [canonical],
            "category": "US pharmacy product ingredient",
            "popularity_rank": existing.get("popularity_rank"),
            "popularity_source": "us_pharmacy_500",
            "evidence_query": " OR ".join(evidence_terms),
        }

    with args.supplements.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            display_name = row["name"]
            normalized = normalization.get(display_name, {})
            components = normalized.get("components", [row["search_term"].split(" OR ")[0]])
            aliases = [normalized.get("alias", ""), *row["search_term"].split(" OR ")]
            entity_id = f"supplement:{slug(display_name)}"
            entities[entity_id] = {
                "entity_id": entity_id,
                "canonical_name": display_name,
                "display_name": display_name,
                "entity_type": "supplement",
                "aliases": unique(aliases),
                "components": unique(components),
                "category": row["category"],
                "popularity_rank": int(row["rank"]),
                "popularity_source": "medguide_trends_2025_2026",
                "evidence_query": row["search_term"],
                **{key: value for key, value in normalized.items() if key not in {"components", "alias"}},
            }

    ordered = sorted(
        entities.values(),
        key=lambda item: (
            item["entity_type"] != "medication",
            item["popularity_rank"] is None,
            item["popularity_rank"] or 9999,
            item["display_name"].casefold(),
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entities": len(ordered), "medications": sum(row["entity_type"] == "medication" for row in ordered), "supplements": sum(row["entity_type"] == "supplement" for row in ordered), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
