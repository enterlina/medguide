from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.artifacts import fingerprint, save_json_atomic
from app.rag.corpus import build_chunks
from app.rag.answerer import answer_from_results
from app.rag.embeddings import FixedHashEmbeddingProvider
from app.rag.retriever import HybridRetriever
from evaluation.dataset import load_questions
from evaluation.metrics import score_question


def run_evaluation(corpus: Path, questions_path: Path, output: Path) -> dict:
    chunks = build_chunks(corpus)
    questions = load_questions(questions_path)
    retriever = HybridRetriever(chunks, FixedHashEmbeddingProvider())
    rows = []
    for question in questions:
        results = retriever.search(question.question, top_k=10)
        metrics = score_question(question, results)
        answer = answer_from_results(question.question, results[:5], "2026-10-26")
        rows.append(
            {
                "query_id": question.query_id,
                "kind": question.kind,
                "answerable": question.answerable_in_corpus,
                "retrieved_source_document_ids": [
                    result.chunk.source_document_id for result in results
                ],
                "answer_status": answer.status,
                **metrics,
            }
        )
    answerable = [row for row in rows if row["answerable"]]
    summary = {
        "run_id": fingerprint(rows)[:16],
        "status": "offline_fixture_engineering_only",
        "created_at": datetime.now(UTC).isoformat(),
        "corpus_hash": fingerprint(corpus.read_text()),
        "benchmark_hash": fingerprint(questions_path.read_text()),
        "question_count": len(rows),
        "answerable_count": len(answerable),
        "document_recall_at_5": sum(row["document_recall"] for row in answerable) / len(answerable),
        "document_recall_at_10": sum(row["document_recall_at_10"] for row in answerable) / len(answerable),
        "ndcg_at_10": sum(row["ndcg_at_10"] for row in answerable) / len(answerable),
        "mrr": sum(row["mrr"] for row in answerable) / len(answerable),
        "complete_evidence_success": sum(row["complete_evidence"] for row in answerable) / len(answerable),
        "gap_abstention_rate": sum(
            row["answer_status"] == "insufficient_evidence" for row in rows if not row["answerable"]
        ) / max(sum(not row["answerable"] for row in rows), 1),
        "embedding_model": "fixed-hash-token-v1",
        "chunk_config": {
            "target_text_tokens": 480,
            "overlap_tokens": 64,
            "max_complete_embedding_input_tokens": 512,
            "silent_truncation": False,
        },
        "retrieval_config": {
            "dense_k": 20,
            "bm25_k": 20,
            "rrf_k": 60,
            "rerank_k": 20,
            "context_top_k": 5
        },
        "provider_runs": {"nebius": "not_run_missing_credentials", "cuda": "not_run"},
        "queries": rows,
    }
    save_json_atomic(output, summary)
    return summary

