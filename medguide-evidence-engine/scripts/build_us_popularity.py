#!/usr/bin/env python3
"""Enrich the 125-entity MedGuide catalog with official US utilization ranks.

MEPS estimates are weighted unique people with a reported prescription event.
NHANES estimates are weighted unique participants reporting a supplement product
in the past 30 days. The two ranks are intentionally kept separate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_CATALOG = Path("data/catalog/entities.json")
DEFAULT_MEPS = Path("data/popularity/raw/meps_2024/h254axlsx.zip")
DEFAULT_NHANES = Path("data/popularity/raw/nhanes_2021_2023/DSQIDS_L.xpt")
DEFAULT_OUTPUT = Path("data/popularity/processed")

NUTRIENT_COLUMNS = {
    "vitamin d": "DSQIVD",
    "vitamin d3": "DSQIVD",
    "vitamin k": "DSQIVK",
    "vitamin k1": "DSQIVK",
    "vitamin k2": "DSQIVK",
    "vitamin c": "DSQIVC",
    "vitamin b12": "DSQIVB12",
    "folic acid": "DSQIFA",
    "folate": "DSQIFA",
    "calcium": "DSQICALC",
    "magnesium": "DSQIMAGN",
    "zinc": "DSQIZINC",
    "iron": "DSQIIRON",
    "potassium": "DSQIPOTA",
    "niacin": "DSQINIAC",
    "choline": "DSQICHL",
    "caffeine": "DSQICAFF",
}

GENERIC_WORDS = {
    "tablet", "tablets", "capsule", "capsules", "oral", "supplement", "supplements",
    "extract", "gummies", "gummy", "powder", "with", "and", "plus", "the",
}


def normalize(value: object) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def entity_terms(entity: dict[str, Any]) -> list[str]:
    values = [entity["canonical_name"], entity.get("display_name", "")]
    values.extend(entity.get("aliases", []))
    values.extend(entity.get("components", []))
    terms = []
    for value in values:
        term = normalize(value)
        if len(term) >= 3 and term not in terms:
            terms.append(term)
    return terms


def meaningful_term(term: str) -> bool:
    words = [word for word in term.split() if word not in GENERIC_WORDS]
    return bool(words) and (len(words) > 1 or len(words[0]) >= 5)


def phrase_match(value: str, terms: list[str]) -> tuple[bool, str | None]:
    padded = f" {value} "
    candidates = sorted((term for term in terms if meaningful_term(term)), key=len, reverse=True)
    for term in candidates:
        if f" {term} " in padded:
            return True, term
    return False, None


def read_meps(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        filename = next(name for name in archive.namelist() if name.lower().endswith(".xlsx") and not name.startswith("__MACOSX"))
        with archive.open(filename) as handle:
            return pd.read_excel(
                handle,
                usecols=["DUPERSID", "RXNAME", "RXDRGNAM", "PERWT24F"],
            )


def aggregate_meps(data: pd.DataFrame, entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    data = data.copy()
    data["normalized_name"] = data["RXDRGNAM"].fillna(data["RXNAME"]).map(normalize)
    results: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if entity["entity_type"] != "medication":
            continue
        terms = entity_terms(entity)
        matches = data["normalized_name"].map(lambda value: phrase_match(value, terms)[0])
        subset = data.loc[matches, ["DUPERSID", "PERWT24F", "normalized_name"]]
        people = subset.groupby("DUPERSID", as_index=False)["PERWT24F"].max()
        matched_names = sorted(subset["normalized_name"].dropna().unique().tolist())
        results[entity["entity_id"]] = {
            "estimated_users": round(float(people["PERWT24F"].sum())) if not people.empty else 0,
            "sample_people": int(len(people)),
            "matched_source_names": matched_names[:25],
            "match_method": "normalized_generic_or_alias_phrase",
            "match_status": "matched" if matched_names else "not_matched",
        }
    ranked = sorted(
        (item for item in results.items() if item[1]["estimated_users"] > 0),
        key=lambda item: (-item[1]["estimated_users"], item[0]),
    )
    for rank, (entity_id, _) in enumerate(ranked, 1):
        results[entity_id]["rank_among_matched_medguide_medications"] = rank
    return results


def nutrient_column(entity: dict[str, Any]) -> str | None:
    # A nutrient total cannot identify a specific combination or delivery form.
    # Example: positive vitamin D does not prove use of a D3 + K2 product.
    if len(entity.get("components", [])) != 1 or "+" in entity["display_name"]:
        return None
    for term in entity_terms(entity):
        if term in NUTRIENT_COLUMNS:
            return NUTRIENT_COLUMNS[term]
    return None


def aggregate_nhanes(data: pd.DataFrame, entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    data = data.copy()
    data["normalized_product"] = data["DSDSUPP"].fillna("").map(normalize)
    results: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if entity["entity_type"] != "supplement":
            continue
        terms = entity_terms(entity)
        column = nutrient_column(entity)
        name_matches = data["normalized_product"].map(lambda value: phrase_match(value, terms)[0])
        if column and column in data:
            nutrient_matches = pd.to_numeric(data[column], errors="coerce").fillna(0) > 0
            matches = name_matches | nutrient_matches
            method = f"product_name_or_positive_{column}"
        else:
            matches = name_matches
            method = "normalized_product_name_phrase"
        subset = data.loc[matches, ["SEQN", "WTDRD1", "normalized_product"]]
        people = subset.groupby("SEQN", as_index=False)["WTDRD1"].max()
        matched_names = sorted(subset.loc[name_matches[matches], "normalized_product"].dropna().unique().tolist())
        results[entity["entity_id"]] = {
            "estimated_30_day_users": round(float(people["WTDRD1"].sum())) if not people.empty else 0,
            "sample_participants": int(len(people)),
            "matched_product_names": matched_names[:25],
            "match_method": method,
            "match_status": "matched" if not people.empty else "not_matched",
            "nutrient_proxy_used": column is not None,
        }
    ranked = sorted(
        (item for item in results.items() if item[1]["estimated_30_day_users"] > 0),
        key=lambda item: (-item[1]["estimated_30_day_users"], item[0]),
    )
    for rank, (entity_id, _) in enumerate(ranked, 1):
        results[entity_id]["rank_among_matched_medguide_supplements"] = rank
    return results


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "entity_id", "display_name", "entity_type", "category", "official_rank",
        "official_source", "estimated_users", "sample_count", "match_status", "match_method",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--meps", type=Path, default=DEFAULT_MEPS)
    parser.add_argument("--nhanes", type=Path, default=DEFAULT_NHANES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    entities = json.loads(args.catalog.read_text(encoding="utf-8"))
    if len(entities) != 125:
        raise ValueError(f"expected 125 catalog entities, found {len(entities)}")
    meps = aggregate_meps(read_meps(args.meps), entities)
    nhanes = aggregate_nhanes(pd.read_sas(args.nhanes, format="xport", encoding="utf-8"), entities)
    retrieved_at = datetime.now(UTC).isoformat()
    enriched = []
    flat_rows = []
    for entity in entities:
        popularity: dict[str, Any]
        if entity["entity_type"] == "medication":
            result = meps.get(entity["entity_id"], {})
            popularity = {
                "source": "MEPS HC-254A 2024",
                "source_url": "https://meps.ahrq.gov/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-254A",
                "rank": result.get("rank_among_matched_medguide_medications"),
                **result,
            }
            estimate = result.get("estimated_users", 0)
            sample = result.get("sample_people", 0)
        else:
            result = nhanes.get(entity["entity_id"], {})
            popularity = {
                "source": "NHANES August 2021-August 2023 DSQIDS_L",
                "source_url": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DSQIDS_L.htm",
                "rank": result.get("rank_among_matched_medguide_supplements"),
                **result,
            }
            estimate = result.get("estimated_30_day_users", 0)
            sample = result.get("sample_participants", 0)
        enriched.append({**entity, "official_popularity": popularity})
        flat_rows.append(
            {
                "entity_id": entity["entity_id"],
                "display_name": entity["display_name"],
                "entity_type": entity["entity_type"],
                "category": entity["category"],
                "official_rank": popularity.get("rank"),
                "official_source": popularity["source"],
                "estimated_users": estimate,
                "sample_count": sample,
                "match_status": popularity.get("match_status", "not_matched"),
                "match_method": popularity.get("match_method", ""),
            }
        )

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "medguide_popularity_125.json").write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_csv(args.output / "medguide_popularity_125.csv", flat_rows)
    manifest = {
        "generated_at": retrieved_at,
        "entity_count": len(enriched),
        "meps_matched": sum(row["entity_type"] == "medication" and row["match_status"] == "matched" for row in flat_rows),
        "nhanes_matched": sum(row["entity_type"] == "supplement" and row["match_status"] == "matched" for row in flat_rows),
        "methodology": {
            "meps": "sum PERWT24F once per unique person and matched catalog medication",
            "nhanes": "sum WTDRD1 once per unique participant and matched catalog supplement; nutrient proxies are explicitly flagged",
            "ranking_scope": "rank within matched MedGuide entities, never a combined drug-plus-supplement rank",
        },
        "sources": {
            "meps": {"sha256": sha256(args.meps), "path": str(args.meps)},
            "nhanes": {"sha256": sha256(args.nhanes), "path": str(args.nhanes)},
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
