from __future__ import annotations

import pytest

from app.providers.nebius import assemble_contexts


def test_context_budget_keeps_complete_fragments_and_trace() -> None:
    rendered, trace = assemble_contexts(
        [
            {"chunk_id": "one", "text": "first complete passage"},
            {"chunk_id": "two", "text": "second complete passage"},
        ],
        max_input_characters=30,
    )
    assert "first complete passage" in rendered
    assert "second complete passage" not in rendered
    assert trace[0]["text"] == "first complete passage"
    assert len(trace[0]["sha256"]) == 64


def test_context_budget_never_silently_truncates() -> None:
    with pytest.raises(ValueError, match="no complete source fragment"):
        assemble_contexts([{"chunk_id": "one", "text": "too long"}], max_input_characters=2)
