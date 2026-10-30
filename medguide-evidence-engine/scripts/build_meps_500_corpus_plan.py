#!/usr/bin/env python3
"""Turn the MEPS top-500 Markdown audit into a safe corpus expansion plan.

The source rows are utilization groups, not normalized ingredients.  This script
preserves every source row, marks broad therapeutic classes as non-ingestible,
separates dosage-form qualifiers, and emits ingredient candidates for the
official-label and PubMed pipelines.  It does not claim that a string split is
an RxNorm validation; every candidate keeps an explicit normalization status.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|$"
)
FORM_SUFFIXES = {
    "NASAL", "OPHTHALMIC", "TOPICAL", "OTIC", "INHALATION", "INJECTABLE",
    "TRANSDERMAL", "RECTAL", "VAGINAL", "ORAL",
}
CLASS_MARKERS = {
    "AGENTS", "ANTIPSYCHOTICS", "ANTICONVULSANTS", "ANTIRHEUMATICS",
    "ANTINEOPLASTICS", "ANTIDIABETIC", "ANTI-INFECTIVES", "ANALGESICS",
    "INHIBITORS", "HORMONES/HORMONE MODIFIERS", "BRONCHODILATOR COMBINATIONS",
    "MUSCLE RELAXANTS", "ANTISPASMODICS",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        rank, name, fills, patients, records = match.groups()
        rows.append(
            {
                "rank": int(rank),
                "source_name": name.strip(),
                "estimated_acquisition_events": int(fills.replace(",", "")),
                "estimated_patients": int(patients.replace(",", "")),
                "sample_acquisition_records": int(records),
            }
        )
    return rows


def is_class(name: str) -> bool:
    return any(marker in name for marker in CLASS_MARKERS)


def normalize_group(row: dict) -> dict:
    name = row["source_name"]
    if is_class(name):
        return {
            **row,
            "group_id": f"meps-group:{slug(name)}",
            "entity_kind": "therapeutic_class",
            "components": [],
            "form": None,
            "normalization_status": "excluded_class_requires_manual_mapping",
            "eligible_for_automated_ingestion": False,
        }

    words = name.split()
    form = words[-1].casefold() if words and words[-1] in FORM_SUFFIXES else None
    ingredient_name = " ".join(words[:-1]) if form else name
    # MEPS renders most combination products with hyphens or slashes.  These
    # are candidates only; RxNorm remains the authority before label ingestion.
    components = [part.strip().casefold() for part in re.split(r"[-/]", ingredient_name) if part.strip()]
    status = "candidate_combination_requires_rxnorm" if len(components) > 1 else "candidate_requires_rxnorm"
    return {
        **row,
        "group_id": f"meps-group:{slug(name)}",
        "entity_kind": "combination" if len(components) > 1 else "ingredient",
        "components": components,
        "form": form,
        "normalization_status": status,
        "eligible_for_automated_ingestion": True,
    }


def build_plan(text: str, existing_catalog: list[dict]) -> dict:
    source_rows = parse_rows(text)
    groups = [normalize_group(row) for row in source_rows]
    existing_terms = {
        slug(value)
        for row in existing_catalog
        for value in [row.get("canonical_name", ""), row.get("display_name", ""), *row.get("aliases", [])]
        if value
    }
    candidates: dict[str, dict] = {}
    for group in groups:
        for component in group["components"]:
            entity_id = f"ingredient:{slug(component)}"
            candidate = candidates.setdefault(
                entity_id,
                {
                    "ingredient_id": entity_id,
                    "canonical_name": component,
                    "display_name": component.title(),
                    "aliases": [],
                    "ingredient_kind": "medication",
                    "normalization_status": "candidate_requires_rxnorm",
                    "source_groups": [],
                    "highest_meps_rank": group["rank"],
                    "already_in_medguide_catalog": slug(component) in existing_terms,
                    "official_label_status": "not_checked",
                    "pubmed_status": "not_searched",
                },
            )
            candidate["source_groups"].append(group["source_name"])
            candidate["highest_meps_rank"] = min(candidate["highest_meps_rank"], group["rank"])
    ordered_candidates = sorted(candidates.values(), key=lambda row: (row["highest_meps_rank"], row["canonical_name"]))
    return {
        "manifest": {
            "source_rows": len(source_rows),
            "ingestible_groups": sum(row["eligible_for_automated_ingestion"] for row in groups),
            "excluded_class_groups": sum(not row["eligible_for_automated_ingestion"] for row in groups),
            "normalized_ingredient_candidates": len(ordered_candidates),
            "already_in_medguide_catalog": sum(row["already_in_medguide_catalog"] for row in ordered_candidates),
            "new_candidates": sum(not row["already_in_medguide_catalog"] for row in ordered_candidates),
        },
        "source_groups": groups,
        "ingredient_candidates": ordered_candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/entities.json"))
    parser.add_argument("--output", type=Path, default=Path("data/catalog/meps_500"))
    args = parser.parse_args()
    plan = build_plan(
        args.source.read_text(encoding="utf-8"),
        json.loads(args.catalog.read_text(encoding="utf-8")),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for key in ("source_groups", "ingredient_candidates"):
        (args.output / f"{key}.json").write_text(
            json.dumps(plan[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    ingestion_catalog = [
        {
            "ingredient_id": row["ingredient_id"],
            "canonical_name": row["canonical_name"],
            "aliases": row["aliases"],
            "ingredient_kind": row["ingredient_kind"],
        }
        for row in plan["ingredient_candidates"]
    ]
    (args.output / "interaction_ingestion_catalog.json").write_text(
        json.dumps(ingestion_catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pubmed_catalog = [
        {
            "entity_id": row["ingredient_id"],
            "canonical_name": row["canonical_name"],
            "display_name": row["display_name"],
            "entity_type": "medication",
            "aliases": row["aliases"],
            "components": [row["canonical_name"]],
            "evidence_query": row["canonical_name"],
        }
        for row in plan["ingredient_candidates"]
    ]
    (args.output / "pubmed_catalog.json").write_text(
        json.dumps(pubmed_catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    empty_links = args.output / "empty_existing_links.json"
    if not empty_links.exists():
        empty_links.write_text("[]\n", encoding="utf-8")
    (args.output / "manifest.json").write_text(
        json.dumps(plan["manifest"], indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(plan["manifest"], indent=2))


if __name__ == "__main__":
    main()
