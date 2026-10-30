from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TOOL = "medguide_supplement_corpus"
DEFAULT_CATALOG = Path("data/supplements/supplements_2025_2026.tsv")
DEFAULT_OUTPUT = Path("data/supplements/discovery")


def configured_ncbi_email() -> str:
    if value := os.getenv("MEDGUIDE_NCBI_EMAIL", "").strip():
        return value
    for path in (Path(".env"), Path("../.env.local")):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MEDGUIDE_NCBI_EMAIL="):
                value = line.partition("=")[2].strip().strip('"').strip("'")
                if value:
                    return value
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover a bounded recent PubMed corpus for the MedGuide supplement catalog."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--email", default=configured_ncbi_email())
    parser.add_argument("--since", default="2021/01/01")
    parser.add_argument("--until", default=datetime.now(UTC).date().strftime("%Y/%m/%d"))
    parser.add_argument("--per-supplement", type=int, default=3, choices=range(1, 6))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_catalog(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 100:
        raise ValueError(f"expected exactly 100 supplements, found {len(rows)}")
    if len({row["rank"] for row in rows}) != 100 or len({row["name"] for row in rows}) != 100:
        raise ValueError("supplement ranks and names must be unique")
    return rows


def quoted_terms(value: str) -> str:
    return " OR ".join(
        f'"{part.strip()}"[Title/Abstract]' for part in value.split(" OR ") if part.strip()
    )


def build_query(row: dict[str, str], since: str, until: str) -> str:
    evidence_filter = (
        '(humans[MeSH Terms]) AND ("Clinical Trial"[Publication Type] '
        'OR "Randomized Controlled Trial"[Publication Type] '
        'OR "Systematic Review"[Publication Type] OR "Meta-Analysis"[Publication Type])'
    )
    return (
        f"({quoted_terms(row['search_term'])}) AND {evidence_filter} "
        f'AND ("{since}"[Date - Publication] : "{until}"[Date - Publication])'
    )


def request_bytes(url: str, params: dict[str, str], email: str, retries: int = 3) -> bytes:
    query = {"tool": TOOL, "email": email, **params}
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(query)}",
        headers={"User-Agent": f"{TOOL}/1.0 ({email})"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def discover_pmids(query: str, limit: int, email: str) -> list[str]:
    payload = request_bytes(
        ESEARCH,
        {
            "db": "pubmed",
            "retmode": "json",
            "retmax": str(limit),
            "sort": "pub date",
            "term": query,
        },
        email,
    )
    result = json.loads(payload).get("esearchresult", {})
    if "idlist" not in result:
        detail = result.get("errorlist") or result.get("ERROR") or "missing idlist"
        raise RuntimeError(f"NCBI ESearch failed: {detail}")
    return result["idlist"]


def text(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext()).strip()


def article_date(article: ET.Element) -> str | None:
    date = article.find(".//ArticleDate")
    if date is None:
        date = article.find(".//PubDate")
    if date is None:
        return None
    year = text(date.find("Year")) or text(date.find("MedlineDate"))
    month = text(date.find("Month"))
    day = text(date.find("Day"))
    return "-".join(part for part in (year, month, day) if part) or None


def history_date(article: ET.Element, status: str) -> str | None:
    node = article.find(f'.//PubMedPubDate[@PubStatus="{status}"]')
    if node is None:
        return None
    return "-".join(
        part for part in (text(node.find("Year")), text(node.find("Month")), text(node.find("Day"))) if part
    ) or None


def revised_date(article: ET.Element) -> str | None:
    node = article.find(".//DateRevised")
    if node is None:
        return None
    return "-".join(
        part for part in (text(node.find("Year")), text(node.find("Month")), text(node.find("Day"))) if part
    ) or None


def publication_events(article: ET.Element) -> list[dict[str, str]]:
    events = []
    for node in article.findall(".//CommentsCorrections"):
        events.append(
            {
                "type": node.attrib.get("RefType", "unknown"),
                "pmid": text(node.find("PMID")),
                "note": text(node.find("RefSource")),
            }
        )
    return events


def integrity_status(publication_types: list[str], events: list[dict[str, str]]) -> str:
    types = {value.lower() for value in publication_types}
    event_types = {event["type"].lower() for event in events}
    if "retracted publication" in types or "retractionin" in event_types:
        return "retracted"
    if "retraction of publication" in types or "retractionof" in event_types:
        return "retraction_notice"
    if event_types.intersection(
        {"erratumin", "erratumfor", "correctedandrepublishedin", "correctedandrepublishedfrom"}
    ):
        return "corrected_or_erratum"
    return "no_integrity_notice_found"


def fetch_articles(pmids: list[str], email: str) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for start in range(0, len(pmids), 100):
        batch = pmids[start : start + 100]
        payload = request_bytes(
            EFETCH,
            {"db": "pubmed", "retmode": "xml", "id": ",".join(batch)},
            email,
        )
        root = ET.fromstring(payload)
        for item in root.findall(".//PubmedArticle"):
            pmid = text(item.find(".//MedlineCitation/PMID"))
            abstract_parts = []
            for part in item.findall(".//Abstract/AbstractText"):
                value = text(part)
                label = part.attrib.get("Label")
                abstract_parts.append(f"{label}: {value}" if label and value else value)
            publication_types = [text(node) for node in item.findall(".//PublicationType")]
            publication_types = [value for value in publication_types if value]
            events = publication_events(item)
            records[pmid] = {
                "pmid": pmid,
                "title": text(item.find(".//ArticleTitle")),
                "journal": text(item.find(".//Journal/Title")),
                "published_at": article_date(item),
                "indexed_at": history_date(item, "pubmed"),
                "source_updated_at": revised_date(item),
                "publication_types": publication_types,
                "publication_events": events,
                "integrity_status": integrity_status(publication_types, events),
                "abstract": "\n".join(value for value in abstract_parts if value),
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        time.sleep(0.36)
    return records


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    queries = [{**row, "query": build_query(row, args.since, args.until)} for row in catalog]
    if args.dry_run:
        print(json.dumps({"supplements": len(queries), "maximum_links": len(queries) * args.per_supplement}, indent=2))
        return
    if not args.email or "@" not in args.email:
        raise SystemExit(
            "Set MEDGUIDE_NCBI_EMAIL or pass --email with a monitored contact address before online discovery."
        )

    args.output.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC).isoformat()
    evidence_version = f"supplements-{datetime.now(UTC).date().isoformat()}"
    links: list[dict] = []
    gaps: list[dict] = []
    pmid_to_supplements: dict[str, list[dict]] = defaultdict(list)
    for index, row in enumerate(queries, start=1):
        pmids = discover_pmids(row["query"], args.per_supplement, args.email)
        if not pmids:
            gaps.append({"rank": int(row["rank"]), "name": row["name"], "query": row["query"]})
        for pmid in pmids:
            association = {
                "rank": int(row["rank"]),
                "name": row["name"],
                "category": row["category"],
                "promoted_for": row["promoted_for"],
                "query": row["query"],
            }
            links.append({"pmid": pmid, **association})
            pmid_to_supplements[pmid].append(association)
        if index < len(queries):
            time.sleep(0.36)

    articles = fetch_articles(sorted(pmid_to_supplements), args.email)
    corpus = []
    for pmid, associations in sorted(pmid_to_supplements.items()):
        article = articles.get(pmid)
        if article is None:
            continue
        corpus.append(
            {
                **article,
                "source": "pubmed",
                "retrieved_at": retrieved_at,
                "last_checked_at": retrieved_at,
                "evidence_version": evidence_version,
                "content_hash": hashlib.sha256(
                    json.dumps(article, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
                "supplements": associations,
                "screening": {
                    "schema_valid": True,
                    "source_span_verified": False,
                    "human_reviewed": False,
                    "admitted_to_evidence": False,
                },
            }
        )

    manifest = {
        "manifest_version": "1.0",
        "created_at": retrieved_at,
        "source": "PubMed E-utilities",
        "source_policy": "Recent discovery only; no efficacy conclusion and no automatic admission.",
        "since": args.since,
        "until": args.until,
        "per_supplement_cap": args.per_supplement,
        "supplement_count": len(catalog),
        "association_count": len(links),
        "unique_publication_count": len(corpus),
        "evidence_gap_count": len(gaps),
        "corpus_record_cap": 500,
        "truncated": False,
        "files": {
            "catalog": str(args.catalog),
            "records": "pubmed_recent.json",
            "associations": "supplement_publication_links.json",
            "gaps": "evidence_gaps.json",
        },
    }
    if len(corpus) > 500:
        raise RuntimeError("corpus exceeds the 500-record cap; revise documented selection rules")
    write_json(args.output / "pubmed_recent.json", corpus)
    write_json(args.output / "supplement_publication_links.json", links)
    write_json(args.output / "evidence_gaps.json", gaps)
    write_json(args.output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
