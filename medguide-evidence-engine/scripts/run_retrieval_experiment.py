from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.bm25 import BM25Index  # noqa: E402
from app.rag.corpus import build_chunks_with_report  # noqa: E402
from app.rag.embeddings import SentenceTransformerEmbeddingProvider  # noqa: E402
from app.rag.models import Chunk  # noqa: E402


EMBEDDING_MODEL_ID = "intfloat/multilingual-e5-base"
RERANKER_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RRF_K = 60


def normalize_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("’", "'")
    return " ".join(normalized.split())


def resolve_snapshot(model_id: str) -> tuple[Path, str]:
    from huggingface_hub import snapshot_download

    path = Path(snapshot_download(model_id, local_files_only=True))
    return path, path.name


def select_questions(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_category: dict[str, list[dict]] = defaultdict(list)
    for query in payload["queries"]:
        by_category[query["category"]].append(query)
    selected = []
    for category_index, category in enumerate(sorted(by_category)):
        by_supplement: dict[str, list[dict]] = defaultdict(list)
        for query in by_category[category]:
            by_supplement[query["supplement_id"]].append(query)
        supplement_ids = sorted(by_supplement)
        for supplement_index, supplement_id in enumerate(supplement_ids):
            candidates = sorted(by_supplement[supplement_id], key=lambda item: item["query_id"])
            template_index = (category_index + supplement_index) % 15
            selected.append(candidates[template_index])
        for supplement_id in supplement_ids[:2]:
            candidates = sorted(by_supplement[supplement_id], key=lambda item: item["query_id"])
            selected.append(candidates[15])
            selected.append(candidates[18])
    if len(selected) != 140 or len({item["query_id"] for item in selected}) != 140:
        raise ValueError(f"representative selection must contain 140 unique questions, got {len(selected)}")
    return selected


def chunk_payload(chunk: Chunk) -> dict:
    return chunk.model_dump(mode="json")


def result_row(
    chunk: Chunk,
    rank: int,
    *,
    bm25_score: float | None,
    vector_score: float | None,
    rrf_score: float | None = None,
    reranker_score: float | None = None,
    context_selected: bool = False,
) -> dict:
    return {
        "rank": rank,
        "chunk_id": chunk.chunk_id,
        "source_document_id": chunk.source_document_id,
        "pmid": chunk.identifiers.get("pmid"),
        "title": chunk.title,
        "study_type": chunk.metadata.get("publication_types", []),
        "source_url": chunk.source_uri,
        "section": chunk.section,
        "chunk_text": chunk.text,
        "bm25_score": bm25_score,
        "vector_similarity": vector_score,
        "rrf_score": rrf_score,
        "reranker_score": reranker_score,
        "context_selected": context_selected,
    }


def annotation_template(questions: list[dict], rankings: list[dict], run_id: str) -> dict:
    labels = []
    ranking_by_query = {item["query_id"]: item for item in rankings}
    for question in questions:
        seen = set()
        for method in ("bm25", "dense", "hybrid"):
            for result in ranking_by_query[question["query_id"]]["methods"][method]["results"]:
                document_id = result["source_document_id"]
                if document_id in seen:
                    continue
                seen.add(document_id)
                labels.append(
                    {
                        "query_id": question["query_id"],
                        "source_document_id": document_id,
                        "pmid": result["pmid"],
                        "label": "not_reviewed",
                        "reviewer": None,
                        "reviewed_at": None,
                        "note": None,
                    }
                )
    return {
        "run_id": run_id,
        "allowed_labels": ["relevant", "partially_relevant", "not_relevant", "not_reviewed"],
        "labels": labels,
    }


def write_html(path: Path, experiment: dict, annotations: dict) -> None:
    bootstrap = json.dumps(
        {
            "run_id": experiment["run_id"],
            "models": experiment["models"],
            "corpus": experiment["corpus"],
            "annotation_count": len(annotations["labels"]),
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedGuide Retrieval Debug Report</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;margin:0;background:#f4f6f8;color:#172033}}main{{max-width:1500px;margin:auto;padding:28px}}h1{{margin:0}}.meta{{color:#657086;margin:8px 0 24px}}details{{background:white;border:1px solid #dce2e8;border-radius:14px;margin:12px 0;overflow:hidden}}summary{{cursor:pointer;padding:16px;font-weight:750}}.query{{padding:0 16px 16px;color:#536078}}.methods{{display:grid;grid-template-columns:repeat(3,minmax(420px,1fr));gap:12px;padding:12px;overflow:auto}}.method{{border:1px solid #e0e5ea;border-radius:10px;overflow:hidden}}.method h3{{margin:0;padding:12px;background:#eef2f6}}.latency{{font-size:12px;color:#657086;padding:0 12px 10px;background:#eef2f6}}.result{{padding:12px;border-top:1px solid #e5e9ed}}.result:first-of-type{{border-top:0}}.title{{font-weight:700}}.chips{{display:flex;flex-wrap:wrap;gap:5px;margin:7px 0}}.chip{{font:11px ui-monospace,monospace;background:#edf1f5;border-radius:5px;padding:3px 5px}}.text{{font-size:12px;line-height:1.45;color:#4a5669;max-height:110px;overflow:auto}}select{{margin-top:8px;padding:5px;border:1px solid #bcc6d0;border-radius:6px}}button{{padding:9px 13px;border:0;border-radius:8px;background:#16213a;color:white;font-weight:700;cursor:pointer}}.summary{{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}}.card{{background:white;border:1px solid #dce2e8;border-radius:10px;padding:12px}}a{{color:#1559b7}}
</style></head><body><main><h1>MedGuide Retrieval Debug Report</h1><p class="meta" id="meta">Loading ranking_results.json…</p><div class="summary" id="summary"></div><p>If automatic loading is blocked, select the two files: <input id="rankingFile" type="file" accept=".json"> <input id="annotationFile" type="file" accept=".json"> <button onclick="loadFiles()">Load files</button></p><button onclick="downloadAnnotations()">Download annotations JSON</button><div id="questions"></div></main>
<script>
const bootstrap={bootstrap}; let experiment=null; let annotations=null; let labels=null; let storageKey='medguide-relevance-'+bootstrap.run_id;
const fmt=x=>x===null||x===undefined?'unavailable':Number(x).toFixed(5);
async function start(){{try{{const [r,a]=await Promise.all([fetch('ranking_results.json').then(x=>x.json()),fetch('relevance_annotations.json').then(x=>x.json())]);initialize(r,a)}}catch(e){{document.getElementById('meta').textContent='Serve this directory with a local HTTP server or choose the JSON files above.'}}}}
async function loadFiles(){{const rf=document.getElementById('rankingFile').files[0],af=document.getElementById('annotationFile').files[0];if(!rf||!af)return;initialize(JSON.parse(await rf.text()),JSON.parse(await af.text()))}}
function initialize(ranking,template){{experiment=ranking;annotations=JSON.parse(localStorage.getItem(storageKey)||JSON.stringify(template));labels=new Map(annotations.labels.map(x=>[x.query_id+'|'+x.source_document_id,x]));render()}}
function render(){{document.getElementById('meta').textContent=`Run ${{experiment.run_id}} · ${{experiment.rankings.length}} questions · ${{experiment.models.embedding.model_id}} · ${{experiment.models.reranker.model_id}}`;document.getElementById('summary').innerHTML=`<div class="card">Chunks: ${{experiment.corpus.chunk_count}}</div><div class="card">Questions: ${{experiment.rankings.length}}</div><div class="card">Evaluable now: 0 (annotations pending)</div>`;const root=document.getElementById('questions');root.innerHTML='';for(const q of experiment.rankings){{const d=document.createElement('details');d.innerHTML=`<summary>${{q.query_id}} · ${{escapeHtml(q.original_question)}}</summary><div class="query">Normalized: ${{escapeHtml(q.normalized_query)}} · ${{escapeHtml(q.category)}} · ${{escapeHtml(q.intent)}}</div><div class="methods"></div>`;const methods=d.querySelector('.methods');for(const name of ['bm25','dense','hybrid']){{const m=q.methods[name];const box=document.createElement('section');box.className='method';box.innerHTML=`<h3>${{name.toUpperCase()}}</h3><div class="latency">Latency: ${{m.latency_ms.toFixed(2)}} ms</div>`;for(const r of m.results){{const key=q.query_id+'|'+r.source_document_id;const label=labels.get(key);const el=document.createElement('div');el.className='result';el.innerHTML=`<div class="title">#${{r.rank}} <a href="${{r.source_url}}" target="_blank">${{escapeHtml(r.title)}}</a></div><div class="chips"><span class="chip">PMID ${{r.pmid||'unavailable'}}</span><span class="chip">${{escapeHtml(r.section)}}</span><span class="chip">BM25 ${{fmt(r.bm25_score)}}</span><span class="chip">Dense ${{fmt(r.vector_similarity)}}</span><span class="chip">RRF ${{fmt(r.rrf_score)}}</span><span class="chip">Reranker ${{fmt(r.reranker_score)}}</span>${{r.context_selected?'<span class="chip">context top-5</span>':''}}</div><div class="text">${{escapeHtml(r.chunk_text)}}</div><select><option value="not_reviewed">Not reviewed</option><option value="relevant">Relevant</option><option value="partially_relevant">Partially relevant</option><option value="not_relevant">Not relevant</option></select>`;const select=el.querySelector('select');select.value=label?.label||'not_reviewed';select.onchange=()=>{{label.label=select.value;label.reviewed_at=select.value==='not_reviewed'?null:new Date().toISOString();localStorage.setItem(storageKey,JSON.stringify(annotations));}};box.appendChild(el)}}methods.appendChild(box)}}root.appendChild(d)}}}}
function escapeHtml(v){{return String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function downloadAnnotations(){{if(!annotations)return;const blob=new Blob([JSON.stringify(annotations,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='relevance_annotations_'+bootstrap.run_id+'.json';a.click();URL.revokeObjectURL(a.href)}}start();
</script></body></html>"""
    path.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real BM25, dense, and hybrid retrieval experiments.")
    parser.add_argument("--corpus", type=Path, default=Path("data/supplements/processed/rag_documents.json"))
    parser.add_argument("--questions", type=Path, default=Path("evaluation/data/golden_question_candidates_2000.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/retrieval-experiment"))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    embedding_path, embedding_revision = resolve_snapshot(EMBEDDING_MODEL_ID)
    reranker_path, reranker_revision = resolve_snapshot(RERANKER_MODEL_ID)
    provider = SentenceTransformerEmbeddingProvider(
        embedding_path,
        model_id=EMBEDDING_MODEL_ID,
        revision=embedding_revision,
        device=args.device,
    )
    chunks, corpus_report = build_chunks_with_report(
        args.corpus,
        max_chunks=500,
        token_counter=provider,
        max_input_tokens=512,
    )
    if corpus_report["exclusions"]:
        raise RuntimeError("exact-token chunking excluded documents; revise selection rules")
    max_tokens = max(
        provider.count(f"passage: {chunk.title}\nsection: {chunk.section}\n{chunk.text}")
        for chunk in chunks
    )
    if max_tokens > 512:
        raise RuntimeError("exact-token audit failed; truncation is forbidden")

    embedding_started = time.perf_counter()
    passage_vectors = provider.embed_passages(chunks)
    embedding_latency_ms = (time.perf_counter() - embedding_started) * 1000
    np.save(args.output / "passage_embeddings.npy", passage_vectors)
    (args.output / "chunks.json").write_text(
        json.dumps([chunk_payload(chunk) for chunk in chunks], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    bm25 = BM25Index([chunk.text for chunk in chunks])
    with (args.output / "bm25_index.pkl").open("wb") as handle:
        pickle.dump(bm25, handle)

    from sentence_transformers import SentenceTransformer

    reranker = SentenceTransformer(str(reranker_path), device=args.device, local_files_only=True)
    reranker.max_seq_length = 512
    reranker_inputs = [f"{chunk.title}\n{chunk.text}" for chunk in chunks]
    reranker_max_tokens = max(
        len(
            reranker.tokenizer(
                value,
                add_special_tokens=True,
                truncation=False,
            )["input_ids"]
        )
        for value in reranker_inputs
    )
    if reranker_max_tokens > 512:
        raise RuntimeError("reranker input exceeds 512 tokens; silent truncation is forbidden")
    reranker_passage_vectors = np.asarray(
        reranker.encode(
            reranker_inputs,
            batch_size=16,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ),
        dtype=np.float32,
    )
    np.save(args.output / "reranker_passage_embeddings.npy", reranker_passage_vectors)
    questions = select_questions(args.questions)
    rankings = []
    csv_rows = []
    for question_index, question in enumerate(questions, start=1):
        original = question["query"]
        normalized = normalize_query(original)

        started = time.perf_counter()
        bm25_scores = bm25.scores(normalized)
        bm25_indices = np.argsort(-bm25_scores)[:20]
        bm25_latency_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        query_vector = provider.embed_query(normalized)
        dense_scores = passage_vectors @ query_vector
        dense_indices = np.argsort(-dense_scores)[:20]
        dense_latency_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        fused: dict[int, float] = {}
        for ranking in (bm25_indices, dense_indices):
            for rank, index in enumerate(ranking, start=1):
                fused[int(index)] = fused.get(int(index), 0.0) + 1.0 / (RRF_K + rank)
        rrf_indices = sorted(fused, key=lambda index: -fused[index])[:20]
        reranker_query = np.asarray(
            reranker.encode(
                [normalized],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0],
            dtype=np.float32,
        )
        reranker_scores = reranker_passage_vectors[rrf_indices] @ reranker_query
        reranked = sorted(
            zip(rrf_indices, reranker_scores, strict=True), key=lambda item: -float(item[1])
        )
        hybrid_latency_ms = (time.perf_counter() - started) * 1000

        methods = {
            "bm25": {
                "latency_ms": bm25_latency_ms,
                "results": [
                    result_row(
                        chunks[int(index)],
                        rank,
                        bm25_score=float(bm25_scores[index]),
                        vector_score=float(dense_scores[index]),
                    )
                    for rank, index in enumerate(bm25_indices[:10], start=1)
                ],
            },
            "dense": {
                "latency_ms": dense_latency_ms,
                "results": [
                    result_row(
                        chunks[int(index)],
                        rank,
                        bm25_score=float(bm25_scores[index]),
                        vector_score=float(dense_scores[index]),
                    )
                    for rank, index in enumerate(dense_indices[:10], start=1)
                ],
            },
            "hybrid": {
                "latency_ms": hybrid_latency_ms,
                "results": [
                    result_row(
                        chunks[index],
                        rank,
                        bm25_score=float(bm25_scores[index]),
                        vector_score=float(dense_scores[index]),
                        rrf_score=float(fused[index]),
                        reranker_score=float(score),
                        context_selected=rank <= 5,
                    )
                    for rank, (index, score) in enumerate(reranked[:10], start=1)
                ],
            },
        }
        document_rankings = {
            method: [result["source_document_id"] for result in payload["results"]]
            for method, payload in methods.items()
        }
        ranking_differences = {}
        for left, right in (("bm25", "dense"), ("bm25", "hybrid"), ("dense", "hybrid")):
            left_documents = set(document_rankings[left])
            right_documents = set(document_rankings[right])
            ranking_differences[f"{left}_vs_{right}"] = {
                "top_1_same": document_rankings[left][0] == document_rankings[right][0],
                "top_10_overlap_count": len(left_documents & right_documents),
                "only_in_left": sorted(left_documents - right_documents),
                "only_in_right": sorted(right_documents - left_documents),
            }
        rankings.append(
            {
                "query_id": question["query_id"],
                "supplement_id": question["supplement_id"],
                "category": question["category"],
                "intent": question["intent"],
                "language": question["language"],
                "original_question": original,
                "normalized_query": normalized,
                "methods": methods,
                "ranking_differences": ranking_differences,
            }
        )
        for method, payload in methods.items():
            for result in payload["results"]:
                csv_rows.append(
                    {
                        "query_id": question["query_id"],
                        "method": method,
                        "latency_ms": payload["latency_ms"],
                        **result,
                    }
                )
        if question_index % 10 == 0:
            print(f"processed {question_index}/{len(questions)} questions", flush=True)

    created_at = datetime.now(UTC).isoformat()
    run_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "created_at": created_at,
                "embedding_revision": embedding_revision,
                "reranker_revision": reranker_revision,
                "questions": [item["query_id"] for item in questions],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:16]
    experiment = {
        "run_id": run_fingerprint,
        "created_at": created_at,
        "models": {
            "embedding": {
                "model_id": EMBEDDING_MODEL_ID,
                "revision": embedding_revision,
                "dimension": provider.dimension,
                "normalized": True,
                "document_prefix": "passage:",
                "query_prefix": "query:",
                "max_input_tokens": 512,
            },
            "reranker": {
                "model_id": RERANKER_MODEL_ID,
                "revision": reranker_revision,
                "score_type": "cosine_similarity_second_stage_bi_encoder",
                "max_input_tokens": 512,
                "max_observed_input_tokens": reranker_max_tokens,
            },
        },
        "corpus": {
            "source_document_count": len(corpus_report["included_source_document_ids"]),
            "chunk_count": len(chunks),
            "max_observed_embedding_input_tokens": max_tokens,
            "excluded_documents": corpus_report["exclusions"],
            "passage_embedding_latency_ms": embedding_latency_ms,
        },
        "selection": {
            "strategy": "14 questions per category: 10 supplement-spanning intents plus 2 typo and 2 multilingual queries",
            "question_count": len(questions),
        },
        "rankings": rankings,
        "evaluation": {
            "evaluable_questions": 0,
            "reason": "verified relevance judgments have not been completed",
            "recall_at_5": None,
            "recall_at_10": None,
            "ndcg_at_10": None,
            "mrr": None,
        },
    }
    (args.output / "ranking_results.json").write_text(
        json.dumps(experiment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (args.output / "ranking_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    annotations = annotation_template(rankings, rankings, run_fingerprint)
    (args.output / "relevance_annotations.json").write_text(
        json.dumps(annotations, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    model_metadata = {
        "run_id": run_fingerprint,
        "created_at": created_at,
        "embedding": experiment["models"]["embedding"],
        "reranker": experiment["models"]["reranker"],
        "artifacts": {
            "embeddings": "passage_embeddings.npy",
            "chunks": "chunks.json",
            "bm25_index": "bm25_index.pkl",
            "reranker_embeddings": "reranker_passage_embeddings.npy",
        },
    }
    (args.output / "model_metadata.json").write_text(
        json.dumps(model_metadata, indent=2) + "\n", encoding="utf-8"
    )
    report_data = {**experiment, "questions": rankings}
    write_html(args.output / "retrieval_debug_report.html", report_data, annotations)
    print(json.dumps({"run_id": run_fingerprint, "questions": len(questions), "chunks": len(chunks)}, indent=2))


if __name__ == "__main__":
    main()
