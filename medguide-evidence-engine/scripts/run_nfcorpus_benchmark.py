from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.bm25 import BM25Index  # noqa: E402
from scripts.run_retrieval_experiment import (  # noqa: E402
    EMBEDDING_MODEL_ID,
    RERANKER_MODEL_ID,
    RRF_K,
    normalize_query,
    resolve_snapshot,
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def read_qrels(path: Path) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result[row["query-id"]][row["corpus-id"]] = int(row["score"])
    return dict(result)


def chunk_documents(documents: list[dict], tokenizer, limit: int = 512) -> list[dict]:
    chunks = []
    for document in documents:
        title = document.get("title", "")
        prefix = f"passage: {title}\nsection: text\n"
        # Decoding token slices can change token boundaries, so retain a small exact-token margin.
        budget = limit - len(tokenizer(prefix, add_special_tokens=True)["input_ids"]) - 4
        token_ids = tokenizer(document["text"], add_special_tokens=False)["input_ids"]
        for ordinal, start in enumerate(range(0, max(len(token_ids), 1), budget)):
            text = tokenizer.decode(token_ids[start : start + budget], skip_special_tokens=True)
            value = prefix + text
            count = len(tokenizer(value, add_special_tokens=True, truncation=False)["input_ids"])
            if count > limit:
                raise RuntimeError(f"token budget exceeded for {document['_id']}: {count}")
            chunks.append(
                {
                    "chunk_id": hashlib.sha256(
                        f"{document['_id']}:{ordinal}:{text}".encode()
                    ).hexdigest(),
                    "document_id": document["_id"],
                    "title": title,
                    "ordinal": ordinal,
                    "text": text,
                    "embedding_input": value,
                }
            )
    return chunks


def collapse(indices, scores, chunks, k=20) -> list[tuple[str, float, int]]:
    seen = set()
    rows = []
    for index in indices:
        document_id = chunks[int(index)]["document_id"]
        if document_id in seen:
            continue
        seen.add(document_id)
        rows.append((document_id, float(scores[int(index)]), int(index)))
        if len(rows) == k:
            break
    return rows


def reciprocal_rank_fusion(
    *rankings: list[str], k: int = 60, limit: int = 100
) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, document_id in enumerate(ranking, 1):
            scores[document_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]


def metrics(ranking: list[str], judgments: dict[str, int]) -> dict[str, float]:
    relevant = {doc for doc, score in judgments.items() if score > 0}
    gains = [judgments.get(doc, 0) for doc in ranking[:10]]
    dcg = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
    ideal = sorted(judgments.values(), reverse=True)[:10]
    idcg = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    first = next((rank for rank, doc in enumerate(ranking[:10], 1) if doc in relevant), None)
    values = {
        "ndcg_at_10": dcg / idcg if idcg else 0.0,
        "mrr_at_10": 1 / first if first else 0.0,
    }
    for cutoff in (5, 10, 20, 50, 100):
        values[f"recall_at_{cutoff}"] = len(set(ranking[:cutoff]) & relevant) / len(relevant)
    for cutoff in (5, 10, 20):
        values[f"hit_at_{cutoff}"] = float(bool(set(ranking[:cutoff]) & relevant))
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/external-benchmarks/nfcorpus")
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    documents = read_jsonl(args.dataset / "corpus.jsonl")
    query_rows = {row["_id"]: row for row in read_jsonl(args.dataset / "queries.jsonl")}
    qrels = read_qrels(args.dataset / "qrels" / "test.tsv")
    queries = [(query_id, query_rows[query_id]["text"]) for query_id in qrels]

    from sentence_transformers import SentenceTransformer

    embedding_path, embedding_revision = resolve_snapshot(EMBEDDING_MODEL_ID)
    reranker_path, reranker_revision = resolve_snapshot(RERANKER_MODEL_ID)
    embedding = SentenceTransformer(str(embedding_path), device=args.device, local_files_only=True)
    embedding.max_seq_length = 512
    reranker = SentenceTransformer(str(reranker_path), device=args.device, local_files_only=True)
    reranker.max_seq_length = 512
    chunks = chunk_documents(documents, embedding.tokenizer)
    passage_cache = args.output / "passage_embeddings.npy"
    reranker_cache = args.output / "reranker_passage_embeddings.npy"
    passage_vectors = (
        np.load(passage_cache)
        if passage_cache.exists()
        else embedding.encode(
            [c["embedding_input"] for c in chunks],
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        ).astype(np.float32)
    )
    if passage_vectors.shape[0] != len(chunks):
        raise RuntimeError("cached E5 embeddings do not match the deterministic chunk count")
    if not passage_cache.exists():
        np.save(passage_cache, passage_vectors)
    reranker_vectors = (
        np.load(reranker_cache)
        if reranker_cache.exists()
        else reranker.encode(
            [f"{c['title']}\n{c['text']}" for c in chunks],
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        ).astype(np.float32)
    )
    if reranker_vectors.shape[0] != len(chunks):
        raise RuntimeError("cached reranker embeddings do not match the deterministic chunk count")
    if not reranker_cache.exists():
        np.save(reranker_cache, reranker_vectors)
    bm25 = BM25Index([f"{c['title']} {c['text']}" for c in chunks])
    chunks_by_document: dict[str, list[int]] = defaultdict(list)
    for index, chunk in enumerate(chunks):
        chunks_by_document[chunk["document_id"]].append(index)

    results = []
    metric_rows: dict[str, list[dict]] = defaultdict(list)
    for number, (query_id, question) in enumerate(queries, 1):
        normalized = normalize_query(question)
        started = time.perf_counter()
        bm_scores = bm25.scores(normalized)
        bm_order = np.argsort(-bm_scores)
        bm_latency = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        qv = embedding.encode(
            [f"query: {normalized}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        dense_scores = passage_vectors @ qv
        dense_order = np.argsort(-dense_scores)
        dense_latency = (time.perf_counter() - started) * 1000
        bm_docs = collapse(bm_order, bm_scores, chunks, k=100)
        dense_docs = collapse(dense_order, dense_scores, chunks, k=100)
        started = time.perf_counter()
        rrf_rows = reciprocal_rank_fusion(
            [d for d, _, _ in bm_docs], [d for d, _, _ in dense_docs], k=RRF_K, limit=100
        )
        rrf_docs = [document_id for document_id, _ in rrf_rows]
        rrf_latency = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        candidates = rrf_docs[:20]
        rq = reranker.encode(
            [normalized], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )[0]
        best_chunk = {}
        for document_id in candidates:
            for i in chunks_by_document[document_id]:
                c = chunks[i]
                score = float(reranker_vectors[i] @ rq)
                if c["document_id"] not in best_chunk or score > best_chunk[c["document_id"]][0]:
                    best_chunk[c["document_id"]] = (score, i)
        reranked_head = sorted(candidates, key=lambda d: best_chunk[d][0], reverse=True)
        reranked_docs = reranked_head + rrf_docs[20:]
        reranked_latency = (time.perf_counter() - started) * 1000
        methods = {
            "bm25": ([d for d, _, _ in bm_docs], bm_latency),
            "dense": ([d for d, _, _ in dense_docs], dense_latency),
            "rrf": (rrf_docs, rrf_latency),
            "reranked": (reranked_docs, reranked_latency),
        }
        payload = {}
        for method, (ranking, latency) in methods.items():
            values = metrics(ranking, qrels[query_id])
            metric_rows[method].append(values)
            payload[method] = {"latency_ms": latency, "ranking": ranking[:100], "metrics": values}
        results.append(
            {
                "query_id": query_id,
                "question": question,
                "gold_documents": qrels[query_id],
                "methods": payload,
            }
        )
        if number % 25 == 0:
            print(f"processed {number}/{len(queries)}", flush=True)
    summary = {
        method: {key: float(np.mean([row[key] for row in rows])) for key in rows[0]}
        for method, rows in metric_rows.items()
    }
    regressions = [
        row["query_id"]
        for row in results
        if row["methods"]["rrf"]["metrics"]["ndcg_at_10"]
        < row["methods"]["dense"]["metrics"]["ndcg_at_10"]
    ]
    output = {
        "dataset": "NFCorpus test",
        "question_count": len(queries),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "models": {
            "embedding": {"id": EMBEDDING_MODEL_ID, "revision": embedding_revision},
            "reranker": {"id": RERANKER_MODEL_ID, "revision": reranker_revision},
        },
        "evaluation_definitions": {
            "relevant": "official NFCorpus qrel score > 0",
            "rrf": "document-level BM25 top-100 + Dense top-100, k=60",
            "mrr_at_10": "reciprocal rank of first relevant document within top 10",
        },
        "summary": summary,
        "rrf_worse_than_dense_query_ids": regressions,
        "queries": results,
    }
    (args.output / "benchmark_results.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    (args.output / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
