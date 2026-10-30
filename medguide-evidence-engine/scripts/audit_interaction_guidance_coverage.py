#!/usr/bin/env python3
"""Audit official-label and displayable-section coverage for the interaction catalog."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


DISPLAYABLE_SECTIONS = {
    "dosage_and_administration", "instructions_for_use", "information_for_patients",
    "indications_and_usage", "drug_interactions", "contraindications", "adverse_reactions",
    "warnings_and_precautions", "warnings_and_cautions", "warnings", "precautions",
    "ask_doctor_or_pharmacist", "do_not_use", "pregnancy", "lactation", "pediatric_use",
    "geriatric_use", "use_in_specific_populations", "interactions_with_medications",
    "recommended_intakes", "health_risks_from_excessive_vitamin_d",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("data/products/us_pharmacy_500/active_ingredients.json"))
    parser.add_argument("--database", type=Path, default=Path("data/interactions/interactions.sqlite3"))
    parser.add_argument("--products", type=Path, default=Path("data/products/us_pharmacy_500/products.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/interactions/guidance_coverage.json"))
    args = parser.parse_args()

    ingredients = json.loads(args.catalog.read_text())
    products = json.loads(args.products.read_text())
    product_ingredient_ids = {item for product in products for item in product["ingredient_ids"]}
    labels_by_ingredient: dict[str, list[dict]] = {}
    with sqlite3.connect(args.database) as connection:
        connection.row_factory = sqlite3.Row
        for row in connection.execute("SELECT source, source_url, product_name, ingredient_ids_json, sections_json FROM labels"):
            label = dict(row)
            label["sections"] = json.loads(label.pop("sections_json"))
            for ingredient_id in json.loads(label.pop("ingredient_ids_json")):
                labels_by_ingredient.setdefault(ingredient_id, []).append(label)

    rows = []
    for ingredient in ingredients:
        labels = labels_by_ingredient.get(ingredient["ingredient_id"], [])
        useful = sorted({section for label in labels for section in label["sections"] if section in DISPLAYABLE_SECTIONS and label["sections"][section]})
        status = "guidance_available" if useful else "label_without_displayable_guidance" if labels else "no_official_source_loaded"
        rows.append({
            "ingredient_id": ingredient["ingredient_id"],
            "name": ingredient["canonical_name"],
            "status": status,
            "labels": len(labels),
            "displayable_sections": useful,
            "sources": sorted({label["source"] for label in labels}),
            "in_pharmacy_products": ingredient["ingredient_id"] in product_ingredient_ids,
        })
    summary = {
        "catalog_ingredients": len(rows),
        "guidance_available": sum(row["status"] == "guidance_available" for row in rows),
        "label_without_displayable_guidance": sum(row["status"] == "label_without_displayable_guidance" for row in rows),
        "no_official_source_loaded": sum(row["status"] == "no_official_source_loaded" for row in rows),
        "pharmacy_product_ingredients": len(product_ingredient_ids),
        "pharmacy_product_guidance_available": sum(row["in_pharmacy_products"] and row["status"] == "guidance_available" for row in rows),
        "pharmacy_product_gaps": sum(row["in_pharmacy_products"] and row["status"] != "guidance_available" for row in rows),
    }
    payload = {"summary": summary, "ingredients": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
