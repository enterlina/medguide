import math

import numpy as np

from scripts.run_bioasq_pilot import embed_checkpointed
from scripts.run_nfcorpus_benchmark import metrics, reciprocal_rank_fusion


def test_rrf_uses_document_ranks_and_deterministic_ties() -> None:
    rows = reciprocal_rank_fusion(["a", "b", "c"], ["b", "a", "d"], k=60)
    assert [item[0] for item in rows[:2]] == ["a", "b"]
    assert math.isclose(rows[0][1], 1 / 61 + 1 / 62)


def test_topic_metrics_include_deep_recall_hits_and_mrr_at_10() -> None:
    ranking = [f"d{i}" for i in range(1, 101)]
    values = metrics(ranking, {"d2": 3, "d30": 2, "d80": 1})
    assert values["recall_at_5"] == 1 / 3
    assert values["recall_at_50"] == 2 / 3
    assert values["recall_at_100"] == 1.0
    assert values["hit_at_5"] == 1.0
    assert values["mrr_at_10"] == 0.5


def test_embedding_checkpoint_is_reused(tmp_path) -> None:
    class FakeModel:
        calls = 0

        def get_sentence_embedding_dimension(self):
            return 2

        def encode(self, inputs, **kwargs):
            self.calls += 1
            return np.asarray([[len(value), 1] for value in inputs], dtype=np.float32)

    model = FakeModel()
    path = tmp_path / "vectors.npy"
    progress = tmp_path / "progress.json"
    first = embed_checkpointed(model, ["a", "bb", "ccc"], path, progress, "fp", batch_size=2)
    calls = model.calls
    second = embed_checkpointed(model, ["a", "bb", "ccc"], path, progress, "fp", batch_size=2)
    np.testing.assert_array_equal(first, second)
    assert model.calls == calls
