from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

PMID_PATTERNS = (
    re.compile(r"^https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/(\d+)/?$", re.IGNORECASE),
    re.compile(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?$", re.IGNORECASE),
    re.compile(r"^(\d+)$"),
)


def extract_pmid(url: str) -> str | None:
    value = url.strip()
    for pattern in PMID_PATTERNS:
        if match := pattern.match(value):
            return match.group(1)
    return None


def load_corpus_pmids(path: Path) -> set[str]:
    documents = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(document["identifiers"]["pmid"])
        for document in documents
        if document.get("identifiers", {}).get("pmid")
    }


def build_report(bioasq_path: Path, corpus_path: Path) -> dict:
    raw = bioasq_path.read_bytes()
    questions = json.loads(raw)["questions"]
    corpus_pmids = load_corpus_pmids(corpus_path)
    bioasq_pmids: set[str] = set()
    matched_questions = []

    for question in questions:
        gold_pmids = {
            pmid
            for url in question.get("documents", [])
            if (pmid := extract_pmid(url)) is not None
        }
        bioasq_pmids.update(gold_pmids)
        overlap = sorted(gold_pmids & corpus_pmids)
        if overlap:
            matched_questions.append(
                {
                    "bioasq_question_id": question["id"],
                    "question": question["body"],
                    "question_type": question["type"],
                    "overlapping_pmids": overlap,
                    "ideal_answer": question.get("ideal_answer", []),
                    "matching_snippets": [
                        snippet
                        for snippet in question.get("snippets", [])
                        if extract_pmid(snippet.get("document", "")) in overlap
                    ],
                }
            )

    overlapping_pmids = sorted(bioasq_pmids & corpus_pmids)
    return {
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "bioasq_release": "training14b",
            "bioasq_source_filename": bioasq_path.name,
            "bioasq_source_sha256": hashlib.sha256(raw).hexdigest(),
            "corpus_source": str(corpus_path),
            "transfer_rule": (
                "A BioASQ relevance judgment transfers only for the original BioASQ question "
                "and exact PMID; PMID presence alone is not a universal relevance label."
            ),
        },
        "summary": {
            "bioasq_question_count": len(questions),
            "bioasq_unique_gold_pmid_count": len(bioasq_pmids),
            "medguide_document_count": len(corpus_pmids),
            "overlapping_pmid_count": len(overlapping_pmids),
            "bioasq_questions_with_overlap": len(matched_questions),
        },
        "overlapping_pmids": overlapping_pmids,
        "matched_questions": matched_questions,
        "interpretation": (
            "No overlap means BioASQ cannot directly label the current MedGuide questions or "
            "documents. BioASQ remains useful as an external retrieval benchmark and schema model."
            if not overlapping_pmids
            else "Matched rows can be evaluated as an external task, without relabeling different MedGuide questions."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit PMID overlap between BioASQ and MedGuide.")
    parser.add_argument("--bioasq", type=Path, required=True)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/supplements/processed/rag_documents.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/external-benchmarks/bioasq14b_overlap.json"),
    )
    args = parser.parse_args()
    report = build_report(args.bioasq, args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
