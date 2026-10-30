from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMID_PATTERNS = (
    re.compile(r"/pubmed/(\d+)/?$", re.IGNORECASE),
    re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?$", re.IGNORECASE),
    re.compile(r"^(\d+)$"),
)


def extract_pmid(value: str) -> str | None:
    for pattern in PMID_PATTERNS:
        if match := pattern.search(value.strip()):
            return match.group(1)
    return None


def text_content(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext()).strip()


def parse_articles(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    records = []
    for citation in root.findall(".//PubmedArticle"):
        pmid = text_content(citation.find(".//MedlineCitation/PMID"))
        article = citation.find(".//MedlineCitation/Article")
        if not pmid or article is None:
            continue
        journal_issue = article.find(".//Journal/JournalIssue")
        pub_date = journal_issue.find("PubDate") if journal_issue is not None else None
        year = text_content(pub_date.find("Year")) if pub_date is not None else ""
        if not year and pub_date is not None:
            medline_date = text_content(pub_date.find("MedlineDate"))
            if match := re.search(r"\b(18|19|20)\d{2}\b", medline_date):
                year = match.group(0)
        sections = []
        for abstract in article.findall(".//Abstract/AbstractText"):
            label = abstract.attrib.get("Label") or abstract.attrib.get("NlmCategory") or "Abstract"
            value = text_content(abstract)
            if value:
                sections.append({"section": label, "text": value})
        records.append(
            {
                "pmid": pmid,
                "title": text_content(article.find("ArticleTitle")),
                "publication_year": int(year) if year else None,
                "journal": text_content(article.find(".//Journal/Title")),
                "abstract_sections": sections,
                "abstract": "\n".join(section["text"] for section in sections),
                "publication_types": [
                    text_content(item)
                    for item in article.findall(".//PublicationTypeList/PublicationType")
                    if text_content(item)
                ],
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return records


def request_batch(pmids: list[str], email: str, api_key: str | None) -> bytes:
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "tool": "medguide_evidence_engine", "email": email}
    if api_key:
        params["api_key"] = api_key
    request = urllib.request.Request(
        EFETCH_URL,
        data=urllib.parse.urlencode(params).encode("ascii"),
        headers={
            "User-Agent": f"medguide-evidence-engine/0.1 ({email})",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def repair_and_load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    valid = []
    invalid_count = 0
    # JSONL is delimited strictly by LF; Unicode line separators may occur inside abstracts.
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        try:
            valid.append(json.loads(line))
        except json.JSONDecodeError:
            invalid_count += 1
    if invalid_count:
        path.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in valid),
            encoding="utf-8",
        )
        print(f"removed {invalid_count} incomplete JSONL line(s)", flush=True)
    return valid


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume-safe BioASQ gold-PMID abstract download.")
    parser.add_argument("--bioasq", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/external/bioasq14b/pubmed_abstracts.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("data/external/bioasq14b/download_manifest.json"))
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    email = os.environ.get("MEDGUIDE_NCBI_EMAIL", "").strip()
    if not email:
        raise RuntimeError("MEDGUIDE_NCBI_EMAIL is required by NCBI usage policy")
    api_key = os.environ.get("MEDGUIDE_NCBI_API_KEY", "").strip() or None
    raw = args.bioasq.read_bytes()
    questions = json.loads(raw)["questions"]
    requested = sorted({pmid for q in questions for value in q.get("documents", []) if (pmid := extract_pmid(value))})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing_records = repair_and_load(args.output)
    existing = {record["pmid"] for record in existing_records}
    pending = [pmid for pmid in requested if pmid not in existing]
    started = datetime.now(UTC).isoformat()
    for offset in range(0, len(pending), args.batch_size):
        batch = pending[offset : offset + args.batch_size]
        for attempt in range(5):
            try:
                records = parse_articles(request_batch(batch, email, api_key))
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2**attempt)
        with args.output.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                existing.add(record["pmid"])
        print(f"downloaded {len(existing)}/{len(requested)}", flush=True)
        time.sleep(0.11 if api_key else 0.34)
    final_records = repair_and_load(args.output)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "started_at": started,
        "benchmark_scope": "BioASQ 14b pooled gold PMID corpus; not official full-PubMed leaderboard corpus",
        "bioasq_sha256": hashlib.sha256(raw).hexdigest(),
        "requested_pmid_count": len(requested),
        "downloaded_record_count": len(existing),
        "missing_record_count": len(set(requested) - existing),
        "records_with_abstract_count": sum(bool(record.get("abstract")) for record in final_records),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
