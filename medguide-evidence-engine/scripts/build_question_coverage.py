from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.dataset import load_user_question_dataset  # noqa: E402


DOSE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:mg|g|mcg|µg|μg|iu|milligram|gram)s?\b|\b(?:daily|twice daily|per day)\b",
    re.IGNORECASE,
)
RESULT_PATTERN = re.compile(
    r"\b(?:result|significant|effect|improv|reduc|increase|decrease|difference|confidence interval|p\s?[<=>])",
    re.IGNORECASE,
)
SAFETY_PATTERN = re.compile(
    r"\b(?:adverse|safety|safe|tolerab|side effect|toxicity|interaction|contraindicat|withdrawal)\w*",
    re.IGNORECASE,
)
COMPARATOR_PATTERN = re.compile(
    r"\b(?:placebo|control group|versus|compared with|comparator|standard care)\b",
    re.IGNORECASE,
)
POPULATION_PATTERN = re.compile(
    r"\b(?:participant|patient|adult|women|men|children|older|pregnan|healthy|diagnos)\w*",
    re.IGNORECASE,
)


def evidence_signals(records: list[dict]) -> dict[str, bool]:
    text = "\n".join(record["abstract"] for record in records)
    publication_types = {
        item.lower() for record in records for item in record["publication_types"]
    }
    return {
        "results": bool(RESULT_PATTERN.search(text)),
        "dose": bool(DOSE_PATTERN.search(text)),
        "safety": bool(SAFETY_PATTERN.search(text)),
        "comparator": bool(COMPARATOR_PATTERN.search(text)),
        "population": bool(POPULATION_PATTERN.search(text)),
        "high_level_design": bool(
            publication_types.intersection(
                {"randomized controlled trial", "systematic review", "meta-analysis"}
            )
        ),
    }


def classify(intent: str, records: list[dict], signals: dict[str, bool]) -> tuple[str, list[str]]:
    if not records:
        return "insufficient_discovery_evidence", ["pubmed_broader_search", "clinicaltrials.gov"]
    if intent == "effectiveness":
        if signals["results"] and signals["population"]:
            return "pubmed_candidates_require_review", []
        return "requires_pmc_full_text", ["pmc_or_publisher_full_text"]
    if intent == "evidence":
        needed = ["clinicaltrials.gov"]
        if signals["high_level_design"]:
            return "pubmed_candidates_plus_registry_check", needed
        return "requires_additional_sources", ["pmc_or_publisher_full_text", *needed]
    if intent == "dose":
        if signals["dose"] and signals["population"]:
            return "pubmed_candidates_require_review", []
        return "requires_pmc_full_text", ["pmc_or_publisher_full_text", "clinicaltrials.gov"]
    if intent == "safety_comparison":
        if signals["safety"] and signals["comparator"]:
            return "pubmed_candidates_require_review", ["official_safety_label_or_database"]
        return "requires_additional_sources", [
            "pmc_or_publisher_full_text",
            "clinicaltrials.gov",
            "official_safety_label_or_database",
        ]
    return "requires_manual_triage", []


def main() -> None:
    parser = argparse.ArgumentParser(description="Map user questions to the supplement discovery corpus.")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("evaluation/data/user_questions_400.json"),
    )
    parser.add_argument(
        "--records",
        type=Path,
        default=Path("data/supplements/discovery/pubmed_recent.json"),
    )
    parser.add_argument(
        "--links",
        type=Path,
        default=Path("data/supplements/discovery/supplement_publication_links.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/question-coverage/question_coverage_400.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/question_coverage_report.md"),
    )
    args = parser.parse_args()

    questions = load_user_question_dataset(args.questions)
    records = json.loads(args.records.read_text(encoding="utf-8"))
    links = json.loads(args.links.read_text(encoding="utf-8"))
    records_by_pmid = {record["pmid"]: record for record in records}
    pmids_by_rank: dict[int, set[str]] = defaultdict(set)
    for link in links:
        pmids_by_rank[int(link["rank"])].add(link["pmid"])

    rows = []
    for question in questions.questions:
        rank = int(question.supplement_id.removeprefix("SUP-"))
        pmids = sorted(pmids_by_rank[rank])
        candidates = [records_by_pmid[pmid] for pmid in pmids if pmid in records_by_pmid]
        signals = evidence_signals(candidates)
        status, additional_sources = classify(question.intent, candidates, signals)
        rows.append(
            {
                "question_id": question.question_id,
                "supplement_id": question.supplement_id,
                "supplement": question.supplement,
                "intent": question.intent,
                "question": question.question,
                "candidate_pmids": pmids,
                "candidate_count": len(pmids),
                "abstract_signals": signals,
                "coverage_status": status,
                "additional_sources_needed": additional_sources,
                "human_reviewed": False,
                "coverage_interpretation": (
                    "Candidate discovery coverage only; not proof that the question is answerable."
                ),
            }
        )

    statuses = Counter(row["coverage_status"] for row in rows)
    intents = Counter((row["intent"], row["coverage_status"]) for row in rows)
    source_needs = Counter(
        source for row in rows for source in row["additional_sources_needed"]
    )
    output = {
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "question_count": len(rows),
            "publication_count": len(records),
            "method": "supplement association plus conservative intent-specific abstract signals",
            "human_reviewed": False,
            "warning": "Coverage is candidate-level and must not be interpreted as evidence sufficiency.",
        },
        "summary": {
            "coverage_statuses": dict(sorted(statuses.items())),
            "by_intent_and_status": {
                f"{intent}:{status}": count
                for (intent, status), count in sorted(intents.items())
            },
            "additional_source_needs": dict(sorted(source_needs.items())),
        },
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    insufficient = [row for row in rows if row["coverage_status"] == "insufficient_discovery_evidence"]
    markdown = [
        "# Question coverage report",
        "",
        f"Generated: {output['metadata']['created_at']}",
        "",
        "This is a conservative discovery-coverage audit, not a clinical answerability or evidence-quality judgment.",
        "",
        "## Summary",
        "",
        "| Coverage status | Questions |",
        "| --- | ---: |",
        *[f"| `{status}` | {count} |" for status, count in sorted(statuses.items())],
        "",
        "## Additional source checks",
        "",
        "| Source class | Questions |",
        "| --- | ---: |",
        *[f"| `{source}` | {count} |" for source, count in sorted(source_needs.items())],
        "",
        "## Questions with no strict PubMed candidates",
        "",
    ]
    if insufficient:
        markdown.extend(
            f"- {row['question_id']} — {row['supplement']} — {row['question']}"
            for row in insufficient
        )
    else:
        markdown.append("- None")
    markdown.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pubmed_candidates_require_review`: the abstract contains intent-relevant signals, but PICO and source spans still require review.",
            "- `pubmed_candidates_plus_registry_check`: publication candidates exist; ClinicalTrials.gov must be searched for registrations, updates, and unpublished results.",
            "- `requires_pmc_full_text`: abstracts do not expose enough intent-specific detail; licensed full text is needed.",
            "- `requires_additional_sources`: PubMed abstracts alone are insufficient; the listed source classes must be checked.",
            "- `insufficient_discovery_evidence`: the strict query found no recent eligible PubMed candidate. This is not proof that research does not exist.",
            "",
        ]
    )
    args.markdown.write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
