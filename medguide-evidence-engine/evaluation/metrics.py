from __future__ import annotations

import math

from evaluation.dataset import Question
from app.rag.models import SearchResult


def score_question(question: Question, results: list[SearchResult]) -> dict[str, float]:
    returned = list(
        dict.fromkeys(result.chunk.source_document_id for result in results)
    )[:10]
    relevant = set(question.relevant_source_document_ids)
    if not question.answerable_in_corpus:
        return {
            "document_recall": 0.0,
            "document_recall_at_5": 0.0,
            "document_recall_at_10": 0.0,
            "ndcg_at_10": 0.0,
            "mrr": 0.0,
            "complete_evidence": 0.0,
        }
    found_at_5 = relevant.intersection(returned[:5])
    found_at_10 = relevant.intersection(returned)
    rank = next((index for index, item in enumerate(returned, 1) if item in relevant), None)
    groups_found = sum(
        any(item in returned[:5] for item in group) for group in question.required_evidence_groups
    )
    dcg = sum(
        1.0 / math.log2(rank_index + 1)
        for rank_index, item in enumerate(returned, 1)
        if item in relevant
    )
    ideal_count = min(len(relevant), 10)
    ideal_dcg = sum(1.0 / math.log2(rank_index + 1) for rank_index in range(1, ideal_count + 1))
    return {
        "document_recall": len(found_at_5) / max(len(relevant), 1),
        "document_recall_at_5": len(found_at_5) / max(len(relevant), 1),
        "document_recall_at_10": len(found_at_10) / max(len(relevant), 1),
        "ndcg_at_10": dcg / ideal_dcg if ideal_dcg else 0.0,
        "mrr": 1.0 / rank if rank else 0.0,
        "complete_evidence": float(groups_found == len(question.required_evidence_groups)),
    }

