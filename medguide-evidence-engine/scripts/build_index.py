from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from app.core.artifacts import fingerprint, save_json_atomic  # noqa: E402
from app.rag.corpus import build_chunks_with_report  # noqa: E402
from app.rag.embeddings import FixedHashEmbeddingProvider, validate_vectors  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("data/fixtures/expected/rag_documents.json"))
    parser.add_argument("--output", type=Path, default=Path("var/index"))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    chunks, selection_report = build_chunks_with_report(args.corpus)
    provider = FixedHashEmbeddingProvider()
    vectors = provider.embed_passages(chunks)
    validate_vectors(vectors, provider.dimension)
    args.output.mkdir(parents=True, exist_ok=True)
    vector_path = args.output / "vectors.npy"
    manifest = {
        "model_id": provider.model_id,
        "model_revision": provider.revision,
        "parser_version": "fixture-v1",
        "chunker_version": "section-budget-v2",
        "dimension": provider.dimension,
        "metric": "inner_product",
        "normalized": provider.normalized,
        "chunk_count": len(chunks),
        "corpus_hash": fingerprint(args.corpus.read_text()),
        "chunk_config": {
            "target_text_tokens": 480,
            "overlap_tokens": 64,
            "max_complete_embedding_input_tokens": 512,
            "silent_truncation": False,
        },
        "selection_report": selection_report,
    }
    manifest["processing_fingerprint"] = fingerprint(
        {
            "corpus_hash": manifest["corpus_hash"],
            "model_id": manifest["model_id"],
            "model_revision": manifest["model_revision"],
            "parser_version": manifest["parser_version"],
            "chunker_version": manifest["chunker_version"],
            "dimension": manifest["dimension"],
            "chunk_config": manifest["chunk_config"],
        }
    )
    previous_manifest_path = args.output / "manifest.json"
    if previous_manifest_path.exists() and not args.rebuild:
        previous = json.loads(previous_manifest_path.read_text())
        if previous.get("processing_fingerprint") == manifest["processing_fingerprint"]:
            print(json.dumps({**manifest, "status": "unchanged_index_reused"}, indent=2))
            return
        manifest["rebuild_reason"] = "source_text_or_processing_configuration_changed"
    elif args.rebuild:
        manifest["rebuild_reason"] = "explicit_rebuild"
    else:
        manifest["rebuild_reason"] = "initial_build"
    np.save(vector_path, vectors)
    save_json_atomic(args.output / "chunks.json", [chunk.model_dump(mode="json") for chunk in chunks])
    save_json_atomic(args.output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

