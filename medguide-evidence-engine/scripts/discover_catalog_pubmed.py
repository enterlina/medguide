#!/usr/bin/env python3
"""Run bounded PubMed discovery for catalog entities not in the existing links."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.discover_supplement_corpus import (
        build_query,
        configured_ncbi_email,
        discover_pmids,
        fetch_articles,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ rather than the repo on sys.path.
    from discover_supplement_corpus import (  # type: ignore[no-redef]
        build_query,
        configured_ncbi_email,
        discover_pmids,
        fetch_articles,
    )


DEFAULT_CATALOG = Path("data/catalog/entities.json")
DEFAULT_EXISTING = Path("data/supplements/discovery/supplement_publication_links.json")
DEFAULT_OUTPUT = Path("data/catalog/discovery")


def normalized(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def select_new_entities(
    entities: list[dict], existing_links: list[dict]
) -> list[dict]:
    existing_names = {normalized(row["name"]) for row in existing_links}
    return [
        entity
        for entity in entities
        if normalized(entity["display_name"]) not in existing_names
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--existing-links", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--email", default=configured_ncbi_email())
    parser.add_argument("--years", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--per-year", type=int, default=2, choices=range(1, 6))
    parser.add_argument(
        "--single-range",
        action="store_true",
        help=(
            "Search the complete year window once per entity instead of running one "
            "request per calendar year. This is faster for broad catalog expansion."
        ),
    )
    parser.add_argument(
        "--per-entity",
        type=int,
        default=5,
        choices=range(1, 21),
        help="Maximum PubMed matches per entity when --single-range is used.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--limit-entities",
        type=int,
        help="Process only the first N selected catalog entities (priority order).",
    )
    parser.add_argument("--offset-entities", type=int, default=0)
    args = parser.parse_args()

    entities = json.loads(args.catalog.read_text(encoding="utf-8"))
    existing = json.loads(args.existing_links.read_text(encoding="utf-8"))
    existing_output_links = []
    existing_links_path = args.output / "entity_publication_links.json"
    if existing_links_path.exists():
        existing_output_links = json.loads(existing_links_path.read_text(encoding="utf-8"))
    # A resumed discovery run must not spend network calls on entities already
    # persisted by an earlier batch.
    selected = select_new_entities(entities, [*existing, *existing_output_links])
    if args.offset_entities < 0:
        raise ValueError("--offset-entities must be non-negative")
    selected = selected[args.offset_entities :]
    if args.limit_entities is not None:
        if args.limit_entities < 1:
            raise ValueError("--limit-entities must be positive")
        selected = selected[: args.limit_entities]
    current_year = datetime.now(UTC).year
    year_ranges = [
        (f"{current_year - args.years + 1}/01/01", f"{current_year}/12/31")
    ] if args.single_range else [
        (f"{year}/01/01", f"{year}/12/31")
        for year in range(current_year - args.years + 1, current_year + 1)
    ]
    queries = []
    for entity in selected:
        row = {"search_term": entity["evidence_query"]}
        for since, until in year_ranges:
            queries.append(
                {
                    **entity,
                    "query": build_query(row, since, until),
                    "year": since[:4],
                }
            )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "entities": len(selected),
                    "years": [since[:4] for since, _ in year_ranges],
                    "searches": len(queries),
                    "maximum_new_links": len(queries) * (
                        args.per_entity if args.single_range else args.per_year
                    ),
                },
                indent=2,
            )
        )
        return
    if not args.email or "@" not in args.email:
        raise SystemExit("Set MEDGUIDE_NCBI_EMAIL or pass --email before online discovery.")

    links = list(existing_output_links)
    gaps = []
    search_errors = []
    associations: dict[str, list[dict]] = defaultdict(list)
    for index, entity in enumerate(queries, 1):
        error: RuntimeError | None = None
        pmids: list[str] = []
        for attempt in range(3):
            try:
                pmids = discover_pmids(
                    entity["query"],
                    args.per_entity if args.single_range else args.per_year,
                    args.email,
                )
                error = None
                break
            except RuntimeError as exc:
                error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        if error is not None:
            search_errors.append(
                {
                    "entity_id": entity["entity_id"],
                    "name": entity["display_name"],
                    "query": entity["query"],
                    "error": str(error),
                }
            )
            continue
        for pmid in pmids:
            association = {
                "entity_id": entity["entity_id"],
                "name": entity["display_name"],
                "entity_type": entity["entity_type"],
                "query": entity["query"],
            }
            links.append({"pmid": pmid, **association})
        if index < len(queries):
            time.sleep(0.36)

    links = list(
        {
            (row["entity_id"], str(row["pmid"])): row
            for row in links
        }.values()
    )
    associations.clear()
    for link in links:
        association = {
            "entity_id": link["entity_id"],
            "name": link["name"],
            "entity_type": link["entity_type"],
            "query": link["query"],
        }
        associations[str(link["pmid"])].append(association)

    linked_entity_ids = {row["entity_id"] for row in links}
    gaps = [
        {
            "entity_id": entity["entity_id"],
            "name": entity["display_name"],
        }
        for entity in selected
        if entity["entity_id"] not in linked_entity_ids
    ]

    articles = fetch_articles(sorted(associations), args.email)
    retrieved_at = datetime.now(UTC).isoformat()
    corpus = [
        {
            **article,
            "source": "pubmed",
            "retrieved_at": retrieved_at,
            "catalog_associations": associations[pmid],
        }
        for pmid, article in sorted(articles.items())
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = {
        "entity_publication_links.json": links,
        "pubmed_recent.json": corpus,
        "evidence_gaps.json": gaps,
        "search_errors.json": search_errors,
    }
    for filename, value in outputs.items():
        (args.output / filename).write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    manifest = {
        "retrieved_at": retrieved_at,
        "catalog_entities": len(entities),
        "existing_entities": len(entities) - len(selected),
        "new_entities_searched": len(selected),
        "publication_links": len(links),
        "unique_publications": len(corpus),
        "entities_without_results": len(gaps),
        "search_errors": len(search_errors),
        "years": (
            list(range(current_year - args.years + 1, current_year + 1))
            if args.single_range
            else [int(since[:4]) for since, _ in year_ranges]
        ),
        "per_year": args.per_year,
        "single_range": args.single_range,
        "per_entity": args.per_entity if args.single_range else None,
        "existing_links_preserved": len(existing_output_links),
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
