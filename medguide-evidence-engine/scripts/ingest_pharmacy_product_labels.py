#!/usr/bin/env python3
"""Ingest exact DailyMed labels from the bounded US pharmacy product catalog."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.adapters import DailyMedSPLAdapter  # noqa: E402
from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.extractor import ConservativeRuleExtractor  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest exact DailyMed SETIDs in bounded batches.")
    parser.add_argument(
        "--products", type=Path, default=ROOT / "data/products/us_pharmacy_500/products.json"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=ROOT / "data/products/us_pharmacy_500/active_ingredients.json",
    )
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--pause-seconds", type=float, default=0.15)
    args = parser.parse_args()
    if args.offset < 0 or not 1 <= args.limit <= 50:
        raise ValueError("Use a non-negative --offset and --limit between 1 and 50")

    products = json.loads(args.products.read_text())
    selected = products[args.offset : args.offset + args.limit]
    catalog = IngredientCatalog.from_json(args.catalog, args.products)
    repository = InteractionRepository(args.database)
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    adapter = DailyMedSPLAdapter()
    extractor = ConservativeRuleExtractor(catalog)
    report = []

    for position, product in enumerate(selected, start=args.offset + 1):
        row = {
            "position": position,
            "product_id": product["product_id"],
            "product_title": product["product_title"],
            "set_id": product["set_id"],
            "ingredient_ids": product["ingredient_ids"],
            "status": "pending",
            "rules": 0,
        }
        if not product["ingredient_ids"]:
            row["status"] = "needs_manual_mapping"
            report.append(row)
            continue
        try:
            xml = adapter.fetch_spl_xml(product["set_id"])
            label = adapter.parse_xml(xml, product["set_id"], product["published"])
            label.product_name = product["product_title"]
            label.ingredient_ids = product["ingredient_ids"]
            rules_by_id = {}
            for ingredient_id in product["ingredient_ids"]:
                for rule in extractor.extract(label, ingredient_id):
                    rules_by_id[rule.interaction_id] = rule
            repository.store_label_and_rules(label, list(rules_by_id.values()))
            row["status"] = "ingested"
            row["label_id"] = label.label_id
            row["rules"] = len(rules_by_id)
        except Exception as exc:  # retain errors so a batch can be resumed safely
            row["status"] = "error"
            row["error"] = str(exc)
        report.append(row)
        print(f"[{position}/{len(products)}] {product['product_id']}: {row['status']}", flush=True)
        time.sleep(args.pause_seconds)

    output = ROOT / "artifacts/interactions/pharmacy_product_ingestion"
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / f"batch_{args.offset:03d}_{args.offset + len(selected):03d}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "selected": len(selected),
        "ingested": sum(row["status"] == "ingested" for row in report),
        "errors": sum(row["status"] == "error" for row in report),
        "needs_manual_mapping": sum(row["status"] == "needs_manual_mapping" for row in report),
        "report": str(report_path),
    }, indent=2))


if __name__ == "__main__":
    main()
