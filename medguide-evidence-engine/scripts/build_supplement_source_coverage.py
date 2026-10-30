from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DSLD_INGREDIENT_GROUPS_URL = "https://api.ods.od.nih.gov/dsld/v9/ingredient-groups/"
DSLD_PRODUCTS_URL = "https://api.ods.od.nih.gov/dsld/v9/browse-products/"


def normalize(value: str) -> str:
    value = re.sub(r"\([^)]*\)", " ", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def score_hit(query: str, source: dict[str, Any]) -> float:
    query_normalized = normalize(query)
    candidates = [source.get("groupName", ""), *(source.get("synonyms") or [])]
    scores = [SequenceMatcher(None, query_normalized, normalize(item)).ratio() for item in candidates]
    if any(normalize(item) == query_normalized for item in candidates):
        return 1.0
    return max(scores, default=0.0)


def fetch_groups(name: str, timeout: float) -> list[dict[str, Any]]:
    url = f"{DSLD_INGREDIENT_GROUPS_URL}?{urllib.parse.urlencode({'method': 'factsheet', 'term': name})}"
    request = urllib.request.Request(url, headers={"User-Agent": "MedGuide source-coverage/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return [hit.get("_source", {}) for hit in payload.get("hits", [])]


def fetch_product_count(name: str, timeout: float) -> int:
    params = urllib.parse.urlencode({"method": "by_keyword", "q": name})
    request = urllib.request.Request(
        f"{DSLD_PRODUCTS_URL}?{params}", headers={"User-Agent": "MedGuide source-coverage/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    total = payload.get("total", 0)
    return int(total.get("value", 0) if isinstance(total, dict) else total)


def source_kind(matches: list[dict[str, Any]], product_count: int) -> str:
    links = [
        (sheet.get("link") or "").casefold()
        for match in matches
        for sheet in match.get("fact_sheets", [])
    ]
    if any("ods.od.nih.gov/factsheets/" in link for link in links):
        return "nih_ods"
    if any(domain in link for link in links for domain in ("nccih.nih.gov", "nccam.nih.gov")):
        return "nccih"
    if product_count:
        return "dsld_product_label_only"
    if any(domain in link for link in links for domain in ("pubmed", "ncbi.nlm.nih.gov", "clinicaltrials.gov")):
        return "research_links_only"
    return "no_official_interaction_source_found"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover official DSLD ingredient groups and linked fact sheets."
    )
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "data/supplements/supplements_2025_2026.tsv"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/supplements/source_coverage"
    )
    parser.add_argument(
        "--normalization",
        type=Path,
        default=ROOT / "data/supplements/supplement_normalization.json",
    )
    parser.add_argument("--pause-seconds", type=float, default=0.08)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    with args.catalog.open(newline="") as stream:
        catalog = list(csv.DictReader(stream, delimiter="\t"))
    normalizations = json.loads(args.normalization.read_text())

    records: list[dict[str, Any]] = []
    for item in catalog:
        name = item["name"]
        normalization = normalizations.get(name, {})
        components = normalization.get("components") or [name]
        record: dict[str, Any] = {
            "rank": int(item["rank"]),
            "category": item["category"],
            "supplement_name": name,
            "queries": components,
            "normalization": normalization,
            "status": "not_found",
            "matches": [],
        }
        try:
            candidates: dict[str, tuple[float, dict[str, Any], str]] = {}
            product_searches = []
            for component in components:
                groups = fetch_groups(component, args.timeout_seconds)
                for group in groups:
                    score = score_hit(component, group)
                    key = str(group.get("groupId") or group.get("groupName"))
                    if score >= 0.55 and (key not in candidates or score > candidates[key][0]):
                        candidates[key] = (score, group, component)
                product_count = fetch_product_count(component, args.timeout_seconds)
                product_searches.append({"query": component, "count": product_count})
                time.sleep(args.pause_seconds)
            accepted = sorted(candidates.values(), key=lambda row: row[0], reverse=True)[:8]
            record["matches"] = [
                {
                    "match_score": round(score, 4),
                    "matched_query": matched_query,
                    "group_id": group.get("groupId"),
                    "group_name": group.get("groupName"),
                    "categories": [value for value in group.get("category", []) if value],
                    "synonyms": group.get("synonyms") or [],
                    "fact_sheets": group.get("factsheets") or [],
                }
                for score, group, matched_query in accepted
            ]
            record["product_label_searches"] = product_searches
            record["product_label_count"] = sum(row["count"] for row in product_searches)
            if accepted:
                record["status"] = "matched"
                record["has_ods_fact_sheet"] = any(
                    "ods.od.nih.gov/factsheets/" in (sheet.get("link") or "")
                    for _, group, _ in accepted
                    for sheet in group.get("factsheets") or []
                )
            else:
                record["has_ods_fact_sheet"] = False
            record["source_class"] = source_kind(
                record["matches"], record["product_label_count"]
            )
        except Exception as exc:
            record.update(status="error", error=str(exc), has_ods_fact_sheet=False)
        records.append(record)
        time.sleep(args.pause_seconds)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "supplement_source_coverage_100.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")

    csv_path = args.output_dir / "supplement_source_coverage_100.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "rank",
                "category",
                "supplement_name",
                "status",
                "best_group_id",
                "best_group_name",
                "normalized_components",
                "source_class",
                "has_ods_fact_sheet",
                "product_label_count",
                "fact_sheet_count",
            ],
        )
        writer.writeheader()
        for record in records:
            best = record["matches"][0] if record["matches"] else {}
            writer.writerow(
                {
                    "rank": record["rank"],
                    "category": record["category"],
                    "supplement_name": record["supplement_name"],
                    "status": record["status"],
                    "best_group_id": best.get("group_id", ""),
                    "best_group_name": best.get("group_name", ""),
                    "normalized_components": " | ".join(record["queries"]),
                    "source_class": record.get("source_class", ""),
                    "has_ods_fact_sheet": record.get("has_ods_fact_sheet", False),
                    "product_label_count": record.get("product_label_count", 0),
                    "fact_sheet_count": len(best.get("fact_sheets", [])),
                }
            )

    summary = {
        "supplements": len(records),
        "matched": sum(row["status"] == "matched" for row in records),
        "with_ods_fact_sheet": sum(bool(row.get("has_ods_fact_sheet")) for row in records),
        "not_found": sum(row["status"] == "not_found" for row in records),
        "errors": sum(row["status"] == "error" for row in records),
        "source_classes": {
            kind: sum(row.get("source_class") == kind for row in records)
            for kind in (
                "nih_ods",
                "nccih",
                "dsld_product_label_only",
                "research_links_only",
                "no_official_interaction_source_found",
            )
        },
        "json": str(json_path),
        "csv": str(csv_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
