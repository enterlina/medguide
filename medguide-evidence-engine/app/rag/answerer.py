from __future__ import annotations

from app.rag.models import Answer, Citation, SearchResult


INJECTION_MARKERS = ("ignore previous", "system prompt", "execute tool", "modify database")
SCOPE_TERMS = ("children", "child", "pregnancy", "pregnant", "citrate", "adverse event")


def answer_from_results(question: str, results: list[SearchResult], corpus_as_of: str) -> Answer:
    usable = [
        result
        for result in results
        if not any(marker in result.chunk.text.lower() for marker in INJECTION_MARKERS)
    ]
    combined_text = " ".join(result.chunk.text.lower() for result in usable)
    missing_scope = [term for term in SCOPE_TERMS if term in question.lower() and term not in combined_text]
    if not usable or usable[0].rerank_score < 0.08 or missing_scope:
        return Answer(
            status="insufficient_evidence",
            question=question,
            answer="The frozen corpus does not contain enough attributable evidence to answer this question.",
            citations=[],
            limitations=["A missing answer in this corpus is not evidence of absence in science."],
            conflicts=[],
            corpus_as_of=corpus_as_of,
            retrieval_metadata={"returned": len(results), "used": 0, "missing_scope": missing_scope},
        )
    citations = [
        Citation(
            chunk_id=result.chunk.chunk_id,
            source_document_id=result.chunk.source_document_id,
            source_uri=result.chunk.source_uri,
            quote=result.chunk.text[:320],
        )
        for result in usable[:3]
    ]
    summaries = " ".join(f"[{index}] {citation.quote}" for index, citation in enumerate(citations, 1))
    return Answer(
        status="research_preview_requires_review",
        question=question,
        answer=f"Source passages retrieved for review: {summaries}",
        citations=citations,
        limitations=[
            "This deterministic preview retrieves source text; it does not establish efficacy or safety.",
            "Study forms, populations, comparators, and outcomes may not be interchangeable.",
        ],
        conflicts=[],
        corpus_as_of=corpus_as_of,
        retrieval_metadata={"returned": len(results), "used": len(citations)},
    )

