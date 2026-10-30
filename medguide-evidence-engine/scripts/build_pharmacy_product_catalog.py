#!/usr/bin/env python3
"""Parse exact DailyMed products and map them to normalized ingredients."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


ROW_RE = re.compile(
    r"^\|\s*((?:OTC|RX)-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\[DailyMed\]\(https://dailymed\.nlm\.nih\.gov/dailymed/drugInfo\.cfm\?setid=([^)]+)\)\s*\|$"
)
SALT_SUFFIXES = {
    "hydrochloride", "hcl", "hydrobromide", "sodium", "potassium", "calcium",
    "besylate", "fumarate", "maleate", "nitrate", "succinate", "tartrate",
    "sulfate", "dihydrate", "polistirex",
}
NON_INGREDIENT_PHRASES = {"anticavity toothpaste", "bactine max wound wash"}


def normalize(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def slug(value: str) -> str:
    return normalize(value).replace(" ", "-")


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        product_id, family, title, published, set_id = match.groups()
        rows.append(
            {
                "product_id": product_id,
                "label_type": "otc" if product_id.startswith("OTC") else "prescription",
                "family": family.strip(),
                "product_title": title.strip(),
                "published": published.strip(),
                "set_id": set_id,
                "source_url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
                "retail_availability": "not_checked",
                "label_status": "label_verified",
            }
        )
    return rows


def active_names(title: str) -> list[str]:
    parentheticals = re.findall(r"\(([^()]+)\)", title)
    if not parentheticals:
        return []
    raw = parentheticals[0].casefold().replace("&", " and ")
    if normalize(raw) in NON_INGREDIENT_PHRASES:
        return []
    # Preserve the punctuation until after the combination has been split.
    # Normalizing the entire phrase first removes commas and silently turns
    # "acetaminophen, aspirin, and caffeine" into one fake ingredient.
    raw = re.sub(r"\b(?:and|with)\b", ",", raw)
    values = []
    for part in raw.split(","):
        value = normalize(part)
        if not value or value in values:
            continue
        values.append(value)
    return values


def base_name(value: str) -> str:
    words = normalize(value).split()
    while words and words[-1] in SALT_SUFFIXES:
        words.pop()
    if words and words[0] in {"buffered", "standardized", "synthetic"}:
        words.pop(0)
    return " ".join(words)


def build_catalog(text: str, active_catalog: list[dict]) -> dict:
    rows = parse_rows(text)
    index: dict[str, str] = {}
    ingredients = {row["ingredient_id"]: dict(row) for row in active_catalog}
    for row in active_catalog:
        for value in [row["canonical_name"], *row.get("aliases", [])]:
            index[normalize(value)] = row["ingredient_id"]
    unmapped: dict[str, dict] = {}
    family_compositions: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    products = []
    for row in rows:
        names = active_names(row["product_title"])
        ingredient_ids = []
        for name in names:
            ingredient_id = index.get(normalize(name)) or index.get(base_name(name))
            if not ingredient_id:
                canonical = base_name(name) or normalize(name)
                ingredient_id = f"ingredient:{slug(canonical)}"
                unmapped.setdefault(
                    ingredient_id,
                    {
                        "ingredient_id": ingredient_id,
                        "canonical_name": canonical,
                        "aliases": [name] if name != canonical else [],
                        "ingredient_kind": "medication",
                    },
                )
            if ingredient_id not in ingredient_ids:
                ingredient_ids.append(ingredient_id)
        family_compositions[normalize(row["family"])].add(tuple(sorted(ingredient_ids)))
        products.append(
            {
                **row,
                "ingredient_names_from_title": names,
                "ingredient_ids": ingredient_ids,
                "normalization_status": "mapped" if ingredient_ids else "needs_manual_mapping",
                "search_aliases": [row["product_title"]],
            }
        )
    for product in products:
        compositions = family_compositions[normalize(product["family"])]
        if len(compositions) == 1 and product["ingredient_ids"]:
            product["search_aliases"].append(product["family"])
    ingredients.update(unmapped)
    used_ids = {
        ingredient_id
        for product in products
        for ingredient_id in product["ingredient_ids"]
    }
    pubmed_entities = [
        {
            "entity_id": ingredient_id,
            "display_name": ingredients[ingredient_id]["canonical_name"],
            "entity_type": "ingredient",
            "evidence_query": ingredients[ingredient_id]["canonical_name"],
        }
        for ingredient_id in sorted(used_ids)
        if ingredient_id in ingredients
    ]
    return {
        "manifest": {
            "products": len(products),
            "otc": sum(row["label_type"] == "otc" for row in products),
            "prescription": sum(row["label_type"] == "prescription" for row in products),
            "mapped_products": sum(bool(row["ingredient_ids"]) for row in products),
            "needs_manual_mapping": sum(not row["ingredient_ids"] for row in products),
            "new_ingredient_candidates": len(unmapped),
            "active_ingredients_after_merge": len(ingredients),
        },
        "products": products,
        "active_ingredients": sorted(ingredients.values(), key=lambda row: row["canonical_name"]),
        "pubmed_entities": pubmed_entities,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--active-catalog", type=Path, default=Path("data/interactions/active_ingredients.json"))
    parser.add_argument("--output", type=Path, default=Path("data/products/us_pharmacy_500"))
    args = parser.parse_args()
    result = build_catalog(
        args.source.read_text(encoding="utf-8"),
        json.loads(args.active_catalog.read_text(encoding="utf-8")),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for key, filename in (
        ("products", "products.json"),
        ("active_ingredients", "active_ingredients.json"),
        ("pubmed_entities", "pubmed_entities.json"),
    ):
        (args.output / filename).write_text(
            json.dumps(result[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (args.output / "manifest.json").write_text(json.dumps(result["manifest"], indent=2) + "\n")
    print(json.dumps(result["manifest"], indent=2))


if __name__ == "__main__":
    main()
