from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.corpus import build_chunks_with_report  # noqa: E402
from app.rag.models import Document  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build section-aware RAG documents from discovery records.")
    parser.add_argument(
        "--records",
        type=Path,
        default=Path("data/supplements/discovery/pubmed_recent.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/supplements/processed/rag_documents.json"),
    )
    parser.add_argument("--max-chunks", type=int, default=500)
    args = parser.parse_args()

    records = json.loads(args.records.read_text(encoding="utf-8"))
    documents = []
    for record in records:
        document = Document(
            source_document_id=f"pubmed:{record['pmid']}",
            source_snapshot=record["content_hash"],
            title=record["title"],
            source="pubmed",
            source_uri=record["source_url"],
            identifiers={"pmid": record["pmid"]},
            metadata={
                "supplements": [item["name"] for item in record["supplements"]],
                "publication_types": record["publication_types"],
                "published_at": record["published_at"],
                "indexed_at": record["indexed_at"],
                "source_updated_at": record["source_updated_at"],
                "last_checked_at": record["last_checked_at"],
                "evidence_version": record["evidence_version"],
                "integrity_status": record.get("integrity_status", "not_checked"),
                "admitted_to_evidence": False,
            },
            sections=[{"section": "Abstract", "text": record["abstract"]}],
        )
        documents.append(document.model_dump(mode="json"))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(documents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _, report = build_chunks_with_report(args.output, max_chunks=args.max_chunks)
    report.update(
        {
            "source_record_count": len(records),
            "document_count": len(documents),
            "section_policy": "PubMed discovery records contain Abstract only; no full text implied.",
            "admitted_to_evidence": False,
        }
    )
    report_path = args.output.with_name("corpus_build_report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "document_count": report["document_count"],
                "actual_chunks": report["actual_chunks"],
                "excluded_document_count": len(report["exclusions"]),
                "max_chunks": report["max_chunks"],
                "admitted_to_evidence": report["admitted_to_evidence"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
