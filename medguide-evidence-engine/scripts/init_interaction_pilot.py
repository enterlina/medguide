from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
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
    print(f"initialized {args.database} with {len(catalog.ingredients)} pilot ingredients")


if __name__ == "__main__":
    main()

