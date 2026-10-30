from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


GAINS = {"relevant": 2, "partially_relevant": 1, "not_relevant": 0}


def metrics(ranked: list[str], judgments: dict[str, int]) -> dict[str, float]:
    relevant = {document_id for document_id, gain in judgments.items() if gain > 0}
    recall_5 = len(relevant.intersection(ranked[:5])) / len(relevant)
    recall_10 = len(relevant.intersection(ranked[:10])) / len(relevant)
    reciprocal_rank = next(
        (1.0 / rank for rank, document_id in enumerate(ranked, 1) if judgments.get(document_id, 0) > 0),
        0.0,
    )
    dcg = sum(
        (2 ** judgments.get(document_id, 0) - 1) / math.log2(rank + 1)
        for rank, document_id in enumerate(ranked[:10], 1)
    )
    ideal = sorted(judgments.values(), reverse=True)[:10]
    idcg = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    return {
        "recall_at_5": recall_5,
        "recall_at_10": recall_10,
        "ndcg_at_10": dcg / idcg if idcg else 0.0,
        "mrr": reciprocal_rank,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate only completely reviewed retrieval pools.")
    parser.add_argument(
        "--rankings",
        type=Path,
        default=Path("artifacts/retrieval-experiment/ranking_results.json"),
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=Path("artifacts/retrieval-experiment/relevance_annotations.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/retrieval-experiment/evaluation_metrics.json"),
    )
    args = parser.parse_args()
    experiment = json.loads(args.rankings.read_text(encoding="utf-8"))
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    labels_by_query: dict[str, dict[str, str]] = defaultdict(dict)
    for item in annotations["labels"]:
        labels_by_query[item["query_id"]][item["source_document_id"]] = item["label"]

    evaluated_rows = []
    excluded = []
    by_method: dict[str, list[dict[str, float]]] = defaultdict(list)
    for query in experiment["rankings"]:
        pooled_documents = {
            result["source_document_id"]
            for method in query["methods"].values()
            for result in method["results"]
        }
        labels = labels_by_query.get(query["query_id"], {})
        incomplete = sorted(
            document_id
            for document_id in pooled_documents
            if labels.get(document_id, "not_reviewed") == "not_reviewed"
        )
        judgments = {
            document_id: GAINS[label]
            for document_id, label in labels.items()
            if label in GAINS
        }
        if incomplete or not any(gain > 0 for gain in judgments.values()):
            excluded.append(
                {
                    "query_id": query["query_id"],
                    "reason": "incomplete_pool" if incomplete else "no_positive_relevance_judgment",
                    "unreviewed_document_count": len(incomplete),
                }
            )
            continue
        method_metrics = {}
        for method_name, method in query["methods"].items():
            ranked = list(
                dict.fromkeys(result["source_document_id"] for result in method["results"])
            )
            values = metrics(ranked, judgments)
            method_metrics[method_name] = values
            by_method[method_name].append(values)
        evaluated_rows.append({"query_id": query["query_id"], "methods": method_metrics})

    summary = {}
    for method_name in ("bm25", "dense", "hybrid"):
        rows = by_method.get(method_name, [])
        summary[method_name] = {
            metric: (sum(row[metric] for row in rows) / len(rows) if rows else None)
            for metric in ("recall_at_5", "recall_at_10", "ndcg_at_10", "mrr")
        }
    output = {
        "run_id": experiment["run_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "question_count": len(experiment["rankings"]),
        "evaluable_question_count": len(evaluated_rows),
        "eligibility_rule": "all pooled top-10 documents reviewed and at least one positive judgment",
        "unreviewed_is_not_irrelevant": True,
        "summary": summary,
        "evaluated_questions": evaluated_rows,
        "excluded_questions": excluded,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evaluable_question_count": len(evaluated_rows), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
