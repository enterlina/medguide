from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.adapters import (  # noqa: E402
    DailyMedSPLAdapter,
    OpenFDALabelAdapter,
    RxNormResolver,
)
from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.extractor import ConservativeRuleExtractor  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded official-label pilot. Never downloads full source archives."
    )
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "data/interactions/pilot_ingredients.json"
    )
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--labels-per-source", type=int, default=1)
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    parser.add_argument(
        "--ingredient-id",
        action="append",
        help="Ingest only the selected normalized ingredient ID; may be repeated.",
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= 50:
        raise ValueError("--limit must be between 1 and 50")
    if args.offset < 0:
        raise ValueError("--offset must be non-negative")
    if not 1 <= args.labels_per_source <= 5:
        raise ValueError("--labels-per-source must be between 1 and 5")

    catalog = IngredientCatalog.from_json(args.catalog)
    repository = InteractionRepository(args.database)
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    resolver = RxNormResolver()
    openfda = OpenFDALabelAdapter()
    dailymed = DailyMedSPLAdapter()
    extractor = ConservativeRuleExtractor(catalog)
    report = []

    ingredients = list(catalog.ingredients.values())
    if args.ingredient_id:
        requested = set(args.ingredient_id)
        unknown = requested.difference(catalog.ingredients)
        if unknown:
            raise ValueError(f"Unknown ingredient IDs: {', '.join(sorted(unknown))}")
        ingredients = [ingredient for ingredient in ingredients if ingredient.ingredient_id in requested]
    else:
        ingredients = ingredients[args.offset : args.offset + args.limit]

    for ingredient in ingredients:
        row: dict[str, object] = {
            "ingredient_id": ingredient.ingredient_id,
            "name": ingredient.canonical_name,
            "sources": [],
            "errors": [],
        }
        try:
            ingredient.rxcui = resolver.find_rxcui(ingredient.canonical_name)
            if not ingredient.rxcui:
                raise ValueError("RxNorm returned no RxCUI")
            repository.upsert_ingredients([ingredient])
        except Exception as exc:
            row["errors"].append(f"rxnorm: {exc}")
            report.append(row)
            continue

        try:
            try:
                labels = openfda.fetch_by_rxcui(
                    ingredient.rxcui, limit=args.labels_per_source
                )
            except Exception:
                # Ingredient RxCUIs are not always indexed on product labels.
                labels = openfda.fetch_by_generic_name(
                    ingredient.canonical_name, limit=args.labels_per_source
                )
            for label in labels:
                label.ingredient_ids = [ingredient.ingredient_id]
                rules = extractor.extract(label, ingredient.ingredient_id)
                repository.store_label_and_rules(label, rules)
                row["sources"].append(
                    {"source": "openfda", "label_id": label.label_id, "rules": len(rules)}
                )
        except Exception as exc:
            row["errors"].append(f"openfda: {exc}")

        try:
            metadata = dailymed.list_by_rxcui(
                ingredient.rxcui, page_size=args.labels_per_source
            )[: args.labels_per_source]
            for item in metadata:
                xml = dailymed.fetch_spl_xml(item["setid"])
                label = dailymed.parse_xml(xml, item["setid"], str(item.get("spl_version")))
                label.ingredient_ids = [ingredient.ingredient_id]
                rules = extractor.extract(label, ingredient.ingredient_id)
                repository.store_label_and_rules(label, rules)
                row["sources"].append(
                    {"source": "dailymed", "label_id": label.label_id, "rules": len(rules)}
                )
        except Exception as exc:
            row["errors"].append(f"dailymed: {exc}")
        report.append(row)
        time.sleep(args.pause_seconds)

    report_path = args.database.with_suffix(".ingestion-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"database": str(args.database), "report": str(report_path), "rows": report}, indent=2))


if __name__ == "__main__":
    main()
