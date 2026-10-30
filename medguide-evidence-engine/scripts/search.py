from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.answerer import answer_from_results  # noqa: E402
from app.rag.corpus import build_chunks  # noqa: E402
from app.rag.embeddings import FixedHashEmbeddingProvider  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--corpus", type=Path, default=Path("data/fixtures/expected/rag_documents.json"))
    parser.add_argument("--form")
    parser.add_argument("--population")
    args = parser.parse_args()
    filters = {key: value for key, value in {"form": args.form, "population": args.population}.items() if value}
    retriever = HybridRetriever(build_chunks(args.corpus), FixedHashEmbeddingProvider())
    results = retriever.search(args.question, filters=filters)
    answer = answer_from_results(args.question, results, "2026-10-26")
    print(json.dumps(answer.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()

