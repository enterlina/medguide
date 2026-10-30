from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.adapters import NIHODSFactSheetAdapter  # noqa: E402
from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.extractor import ConservativeRuleExtractor  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


# Explicit mapping prevents a product or trendy compound from being silently
# treated as if NIH had published an ingredient-specific fact sheet for it.
ODS_FACT_SHEETS = {
    "ingredient:calcium": "Calcium",
    "ingredient:iron": "Iron",
    "ingredient:magnesium": "Magnesium",
    "ingredient:vitamin-d": "VitaminD",
    "ingredient:vitamin-k": "VitaminK",
    "ingredient:vitamin-e": "VitaminE",
    "ingredient:multivitamin": "MVMS",
    "ingredient:riboflavin": "Riboflavin",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest bounded official NIH ODS fact sheets.")
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "data/interactions/pilot_ingredients.json"
    )
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    args = parser.parse_args()

    catalog = IngredientCatalog.from_json(args.catalog)
    repository = InteractionRepository(args.database)
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    adapter = NIHODSFactSheetAdapter()
    extractor = ConservativeRuleExtractor(catalog)
    report: list[dict[str, object]] = []

    for ingredient_id, slug in ODS_FACT_SHEETS.items():
        row: dict[str, object] = {"ingredient_id": ingredient_id, "slug": slug}
        try:
            label = adapter.fetch(slug)
            label.ingredient_ids = [ingredient_id]
            rules = extractor.extract(label, ingredient_id)
            repository.store_label_and_rules(label, rules)
            row.update(
                status="ingested",
                sections=sorted(label.sections),
                rules=len(rules),
                source_url=str(label.source_url),
            )
        except Exception as exc:
            row.update(status="failed", error=str(exc))
        report.append(row)

    report_path = args.database.with_name("ods.ingestion-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"database": str(args.database), "report": str(report_path), "rows": report}, indent=2))


if __name__ == "__main__":
    main()
