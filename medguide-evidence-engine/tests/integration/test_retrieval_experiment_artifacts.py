import json
from pathlib import Path

import numpy as np


ROOT = Path("artifacts/retrieval-experiment")


def test_persisted_real_embedding_artifacts_are_aligned() -> None:
    chunks = json.loads((ROOT / "chunks.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "model_metadata.json").read_text(encoding="utf-8"))
    vectors = np.load(ROOT / "passage_embeddings.npy")
    assert len(chunks) == vectors.shape[0] == 352
    assert vectors.shape[1] == metadata["embedding"]["dimension"] == 768
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-4, atol=1e-4)
    assert metadata["embedding"]["model_id"] == "intfloat/multilingual-e5-base"
    assert metadata["embedding"]["normalized"] is True


def test_each_debug_ranking_has_real_scores_and_separate_annotations() -> None:
    rankings = json.loads((ROOT / "ranking_results.json").read_text(encoding="utf-8"))
    annotations = json.loads((ROOT / "relevance_annotations.json").read_text(encoding="utf-8"))
    assert len(rankings["rankings"]) == 140
    for query in rankings["rankings"]:
        assert set(query["methods"]) == {"bm25", "dense", "hybrid"}
        for result in query["methods"]["bm25"]["results"]:
            assert result["bm25_score"] is not None
        for result in query["methods"]["dense"]["results"]:
            assert result["vector_similarity"] is not None
        for result in query["methods"]["hybrid"]["results"]:
            assert result["rrf_score"] is not None
            assert result["reranker_score"] is not None
    assert annotations["run_id"] == rankings["run_id"]
    assert all(item["label"] == "not_reviewed" for item in annotations["labels"])


def test_unreviewed_experiment_does_not_publish_ranking_quality_metrics() -> None:
    metrics = json.loads((ROOT / "evaluation_metrics.json").read_text(encoding="utf-8"))
    assert metrics["evaluable_question_count"] == 0
    assert metrics["unreviewed_is_not_irrelevant"] is True
    for method in metrics["summary"].values():
        assert all(value is None for value in method.values())

