from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.download_bioasq_pubmed import extract_pmid  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]


def prepare(bioasq_path: Path, records_path: Path, seed: int, pilot_size: int) -> dict:
    questions = json.loads(bioasq_path.read_text(encoding="utf-8"))["questions"]
    records = load_jsonl(records_path)
    records_by_pmid = {record["pmid"]: record for record in records}
    rows = []
    missing_pmids: set[str] = set()
    missing_abstract_pmids: set[str] = set()
    for question in questions:
        gold = sorted(
            {pmid for value in question.get("documents", []) if (pmid := extract_pmid(value))}
        )
        available = [pmid for pmid in gold if records_by_pmid.get(pmid, {}).get("abstract")]
        missing_pmids.update(pmid for pmid in gold if pmid not in records_by_pmid)
        missing_abstract_pmids.update(
            pmid
            for pmid in gold
            if pmid in records_by_pmid and not records_by_pmid[pmid].get("abstract")
        )
        rows.append(
            {
                "query_id": question["id"],
                "question": question["body"],
                "question_type": question["type"],
                "gold_pmids": gold,
                "available_gold_pmids": available,
                "gold_coverage": len(available) / len(gold) if gold else 0.0,
            }
        )
    rng = random.Random(seed)
    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_type[row["question_type"]].append(row)
    selected = []
    base, remainder = divmod(pilot_size, len(by_type))
    for index, question_type in enumerate(sorted(by_type)):
        candidates = sorted(by_type[question_type], key=lambda row: row["query_id"])
        selected.extend(rng.sample(candidates, base + (index < remainder)))
    selected.sort(key=lambda row: row["query_id"])
    return {
        "metadata": {
            "seed": seed,
            "pilot_size": pilot_size,
            "selection": "stratified random sample by BioASQ question type",
        },
        "summary": {
            "question_count": len(rows),
            "record_count": len(records),
            "records_with_abstract": sum(bool(record.get("abstract")) for record in records),
            "missing_gold_pmid_count": len(missing_pmids),
            "gold_pmids_without_abstract_count": len(missing_abstract_pmids),
            "questions_with_complete_gold_coverage": sum(row["gold_coverage"] == 1 for row in rows),
            "pilot_by_type": dict(Counter(row["question_type"] for row in selected)),
        },
        "missing_gold_pmids": sorted(missing_pmids),
        "gold_pmids_without_abstract": sorted(missing_abstract_pmids),
        "pilot_questions": selected,
        "all_questions": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bioasq", type=Path, required=True)
    parser.add_argument(
        "--records", type=Path, default=Path("data/external/bioasq14b/pubmed_abstracts_v2.jsonl")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/external-benchmarks/bioasq14b/coverage_and_selection.json"),
    )
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--pilot-size", type=int, default=200)
    args = parser.parse_args()
    report = prepare(args.bioasq, args.records, args.seed, args.pilot_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
