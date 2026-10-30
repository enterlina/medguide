from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.bm25 import BM25Index  # noqa: E402
from scripts.run_nfcorpus_benchmark import (  # noqa: E402
    chunk_documents,
    collapse,
    metrics,
    reciprocal_rank_fusion,
)
from scripts.run_retrieval_experiment import (  # noqa: E402
    EMBEDDING_MODEL_ID,
    RRF_K,
    normalize_query,
    resolve_snapshot,
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def embed_checkpointed(
    model,
    inputs: list[str],
    path: Path,
    progress_path: Path,
    fingerprint: str,
    batch_size: int = 32,
) -> np.ndarray:
    dimension = int(model.get_sentence_embedding_dimension())
    progress = {}
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
    can_resume = (
        path.exists()
        and progress.get("processing_fingerprint") == fingerprint
        and progress.get("shape") == [len(inputs), dimension]
    )
    start = int(progress.get("next_index", 0)) if can_resume else 0
    mode = "r+" if can_resume else "w+"
    vectors = np.lib.format.open_memmap(
        path, mode=mode, dtype=np.float32, shape=(len(inputs), dimension)
    )
    for offset in range(start, len(inputs), batch_size):
        stop = min(offset + batch_size, len(inputs))
        vectors[offset:stop] = model.encode(
            inputs[offset:stop],
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
        vectors.flush()
        progress_path.write_text(
            json.dumps(
                {
                    "processing_fingerprint": fingerprint,
                    "shape": [len(inputs), dimension],
                    "next_index": stop,
                    "complete": stop == len(inputs),
                },
                indent=2,
            )
            + "\n"
        )
        if stop % 320 == 0 or stop == len(inputs):
            print(f"embedded {stop}/{len(inputs)} chunks", flush=True)
    return np.asarray(vectors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--records", type=Path, default=Path("data/external/bioasq14b/pubmed_abstracts_v2.jsonl")
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("artifacts/external-benchmarks/bioasq14b/coverage_and_selection.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/external-benchmarks/bioasq14b/pilot")
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = [record for record in load_jsonl(args.records) if record.get("abstract")]
    documents = [
        {"_id": record["pmid"], "title": record["title"], "text": record["abstract"]}
        for record in records
    ]
    metadata_by_pmid = {
        record["pmid"]: {
            key: record.get(key) for key in ("title", "journal", "publication_year", "source_url")
        }
        for record in records
    }
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    questions = selection["pilot_questions"]

    from sentence_transformers import SentenceTransformer

    model_path, revision = resolve_snapshot(EMBEDDING_MODEL_ID)
    model = SentenceTransformer(str(model_path), device=args.device, local_files_only=True)
    model.max_seq_length = 512
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "records": file_sha256(args.records),
                "model": EMBEDDING_MODEL_ID,
                "revision": revision,
                "limit": 512,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    manifest_path = args.output / "index_manifest.json"
    chunks_path = args.output / "chunks.json"
    vectors_path = args.output / "passage_embeddings.npy"
    progress_path = args.output / "embedding_progress.json"
    bm25_path = args.output / "bm25_index.pkl"
    cache_hit = False
    if (
        manifest_path.exists()
        and chunks_path.exists()
        and vectors_path.exists()
        and bm25_path.exists()
    ):
        manifest = json.loads(manifest_path.read_text())
        cache_hit = manifest.get("processing_fingerprint") == fingerprint
    if cache_hit:
        chunks = json.loads(chunks_path.read_text())
        vectors = np.load(vectors_path)
        with bm25_path.open("rb") as handle:
            bm25 = pickle.load(handle)
    else:
        progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
        if chunks_path.exists() and progress.get("processing_fingerprint") == fingerprint:
            chunks = json.loads(chunks_path.read_text())
        else:
            chunks = chunk_documents(documents, model.tokenizer)
            chunks_path.write_text(json.dumps(chunks, ensure_ascii=False) + "\n")
        vectors = embed_checkpointed(
            model,
            [chunk["embedding_input"] for chunk in chunks],
            vectors_path,
            progress_path,
            fingerprint,
        )
        bm25 = BM25Index([f"{chunk['title']} {chunk['text']}" for chunk in chunks])
        with bm25_path.open("wb") as handle:
            pickle.dump(bm25, handle)
        manifest_path.write_text(
            json.dumps(
                {
                    "processing_fingerprint": fingerprint,
                    "model_id": EMBEDDING_MODEL_ID,
                    "model_revision": revision,
                    "dimension": int(vectors.shape[1]),
                    "normalized": True,
                    "max_input_tokens": 512,
                    "document_count": len(documents),
                    "chunk_count": len(chunks),
                },
                indent=2,
            )
            + "\n"
        )
    if vectors.shape[0] != len(chunks):
        raise RuntimeError("chunk/vector cache alignment failed")

    metric_rows: dict[str, list[dict]] = defaultdict(list)
    results = []
    for number, question in enumerate(questions, 1):
        query = normalize_query(question["question"])
        started = time.perf_counter()
        bm_scores = bm25.scores(query)
        bm_docs = collapse(np.argsort(-bm_scores), bm_scores, chunks, 100)
        bm_latency = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        query_vector = model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        dense_scores = vectors @ query_vector
        dense_docs = collapse(np.argsort(-dense_scores), dense_scores, chunks, 100)
        dense_latency = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        rrf_docs = [
            doc
            for doc, _ in reciprocal_rank_fusion(
                [doc for doc, _, _ in bm_docs],
                [doc for doc, _, _ in dense_docs],
                k=RRF_K,
                limit=100,
            )
        ]
        rrf_latency = (time.perf_counter() - started) * 1000
        judgments = {pmid: 1 for pmid in question["available_gold_pmids"]}
        methods = {
            "bm25": ([doc for doc, _, _ in bm_docs], bm_latency),
            "dense": ([doc for doc, _, _ in dense_docs], dense_latency),
            "rrf": (rrf_docs, rrf_latency),
        }
        method_payload = {}
        for name, (ranking, latency) in methods.items():
            values = metrics(ranking, judgments) if judgments else None
            if values:
                metric_rows[name].append(values)
            method_payload[name] = {
                "latency_ms": latency,
                "ranking": [{"pmid": pmid, **metadata_by_pmid[pmid]} for pmid in ranking],
                "metrics": values,
            }
        results.append({**question, "methods": method_payload})
        if number % 20 == 0:
            print(f"processed {number}/{len(questions)}", flush=True)
    summary = {
        name: {key: float(np.mean([row[key] for row in rows])) for key in rows[0]}
        for name, rows in metric_rows.items()
    }
    with (args.output / "per_query_rankings.jsonl").open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output / "benchmark_summary.json").write_text(
        json.dumps(
            {
                "benchmark_label": "BioASQ 14b pooled-gold benchmark on a restricted PubMed corpus — not the official full-PubMed leaderboard benchmark.",
                "pilot_question_count": len(questions),
                "complete_gold_coverage_question_count": sum(
                    row["gold_coverage"] == 1 for row in questions
                ),
                "cache_hit": cache_hit,
                "summary": summary,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
