#!/usr/bin/env python3
"""Merge a staged MEPS interaction batch into the active local corpus.

Existing rules, review statuses, and audit events always win.  New staged rules
remain ``extracted`` and are never promoted to a reviewed status here.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


TABLE_COLUMNS = {
    "ingredients": "ingredient_id,canonical_name,rxcui,aliases_json,ingredient_kind",
    "labels": "label_id,source,source_url,set_id,version,effective_time,product_name,rxcui,ingredient_ids_json,sections_json,content_hash",
    "interaction_rules": "interaction_id,subject_id,object_id,interaction_type,status,validation_status,payload_json,label_id",
}


def merge_catalog(base: list[dict], staged: list[dict]) -> list[dict]:
    merged = {row["ingredient_id"]: row for row in staged}
    # The established pilot definitions contain curated aliases and supplement
    # classifications, so they intentionally override generated MEPS candidates.
    merged.update({row["ingredient_id"]: row for row in base})
    return sorted(merged.values(), key=lambda row: row["canonical_name"].casefold())


def merge_databases(active: Path, staged: Path) -> dict[str, int]:
    if not staged.exists():
        raise FileNotFoundError(staged)
    connection = sqlite3.connect(active)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("ATTACH DATABASE ? AS staged", (str(staged),))
        before = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLE_COLUMNS
        }
        for table, columns in TABLE_COLUMNS.items():
            connection.execute(
                f"INSERT OR IGNORE INTO main.{table} ({columns}) SELECT {columns} FROM staged.{table}"
            )
        connection.commit()
        after = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLE_COLUMNS
        }
    finally:
        connection.close()
    return {f"new_{table}": after[table] - before[table] for table in TABLE_COLUMNS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-catalog", type=Path, default=Path("data/interactions/pilot_ingredients.json"))
    parser.add_argument("--staged-catalog", type=Path, default=Path("data/catalog/meps_500/interaction_ingestion_catalog.json"))
    parser.add_argument("--active-catalog", type=Path, default=Path("data/interactions/active_ingredients.json"))
    parser.add_argument("--active-database", type=Path, default=Path("data/interactions/interactions.sqlite3"))
    parser.add_argument("--staged-database", type=Path, default=Path("data/interactions/meps_500.sqlite3"))
    args = parser.parse_args()
    catalog = merge_catalog(
        json.loads(args.base_catalog.read_text(encoding="utf-8")),
        json.loads(args.staged_catalog.read_text(encoding="utf-8")),
    )
    args.active_catalog.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    result = merge_databases(args.active_database, args.staged_database)
    print(json.dumps({"active_ingredients": len(catalog), **result}, indent=2))


if __name__ == "__main__":
    main()
