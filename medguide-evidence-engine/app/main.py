from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from app.models.api import AskRequest, SearchRequest
from app.interactions.catalog import IngredientCatalog
from app.interactions.engine import InteractionEngine
from app.interactions.models import (
    AuthenticatedRuleReviewRequest,
    InteractionCheckRequest,
    InteractionCheckResponse,
    ReviewQueueResponse,
    ReviewNoteRequest,
    ReviewSummaryResponse,
    RuleDetailResponse,
    RuleReviewEvent,
    RuleReviewRequest,
    ValidationStatus,
)
from app.interactions.repository import InteractionRepository
from app.core.security import (
    ReviewerPrincipal,
    ReviewerRole,
    require_admin,
    require_reviewer,
    require_role,
)
from app.rag.answerer import answer_from_results
from app.rag.corpus import build_chunks
from app.rag.embeddings import FixedHashEmbeddingProvider
from app.rag.retriever import HybridRetriever


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "data" / "fixtures" / "expected" / "rag_documents.json"
chunks = build_chunks(CORPUS)
retriever = HybridRetriever(chunks, FixedHashEmbeddingProvider())
interaction_catalog = IngredientCatalog.from_json(
    ROOT / "data" / "products" / "us_pharmacy_500" / "active_ingredients.json",
    ROOT / "data" / "products" / "us_pharmacy_500" / "products.json",
)
interaction_repository = InteractionRepository(
    ROOT / "data" / "interactions" / "interactions.sqlite3"
)
interaction_repository.upsert_ingredients(list(interaction_catalog.ingredients.values()))
interaction_engine = InteractionEngine(interaction_catalog, interaction_repository)

app = FastAPI(title="MedGuide Evidence Engine", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str | int]:
    return {"status": "ready", "index": "offline-ci", "chunks": len(chunks)}


@app.post("/api/v1/ingestion/runs", dependencies=[Depends(require_admin)])
def create_ingestion_run() -> dict:
    raise HTTPException(
        status_code=501,
        detail={"code": "OFFLINE_ONLY", "message": "use the bounded offline seed command"},
    )


@app.post("/api/v1/index/build", dependencies=[Depends(require_admin)])
def create_index_build() -> dict:
    raise HTTPException(
        status_code=501,
        detail={"code": "OFFLINE_ONLY", "message": "use scripts/build_index.py"},
    )


@app.post("/api/v1/search")
def search(request: SearchRequest) -> dict:
    results = retriever.search(request.query, filters=request.filters, top_k=request.top_k)
    if not results:
        raise HTTPException(status_code=404, detail={"code": "NO_RESULTS", "message": "No chunks match the requested scope."})
    return {
        "results": [
            {
                "chunk_id": result.chunk.chunk_id,
                "source_document_id": result.chunk.source_document_id,
                "section": result.chunk.section,
                "snippet": result.chunk.text,
                "source_uri": result.chunk.source_uri,
                "identifiers": result.chunk.identifiers,
                "scores": {
                    "dense": result.dense_score,
                    "bm25": result.bm25_score,
                    "rrf": result.rrf_score,
                    "rerank": result.rerank_score,
                },
                "source_snapshot": result.chunk.source_snapshot,
            }
            for result in results
        ],
        "corpus_as_of": "2026-10-26",
    }


@app.post("/api/v1/ask")
def ask(request: AskRequest) -> dict:
    results = retriever.search(request.question, filters=request.filters, top_k=5)
    return answer_from_results(request.question, results, "2026-10-26").model_dump(mode="json")


@app.post("/api/interactions/check", response_model=InteractionCheckResponse)
def check_interactions(request: InteractionCheckRequest) -> InteractionCheckResponse:
    """Check pre-extracted rules; absence of a rule is never returned as SAFE."""
    return interaction_engine.check(request)


@app.get("/api/interactions/catalog")
def interaction_search_catalog() -> dict[str, list[str]]:
    """Return normalized ingredients and exact pharmacy-product names for autosuggest."""
    covered = interaction_repository.covered_ingredients()
    ingredients = sorted(
        {
            name
            for item in interaction_catalog.ingredients.values()
            if item.ingredient_id in covered
            for name in [item.canonical_name, *item.aliases]
            if name.strip()
        },
        key=str.casefold,
    )
    products = sorted(
        {
            alias
            for product in interaction_catalog.products
            if product.get("ingredient_ids") and all(item in covered for item in product["ingredient_ids"])
            for alias in product.get("search_aliases", [])
        },
        key=str.casefold,
    )
    return {"ingredients": ingredients, "products": products}


@app.get(
    "/api/interactions/review",
    response_model=ReviewQueueResponse,
)
def interaction_review_queue(
    status: ValidationStatus = ValidationStatus.EXTRACTED,
    interaction_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> ReviewQueueResponse:
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="invalid pagination")
    rules, total = interaction_repository.review_queue(
        status, limit, offset, interaction_type
    )
    return ReviewQueueResponse(rules=rules, total=total, limit=limit, offset=offset)


@app.get("/api/interactions/review/session", response_model=ReviewerPrincipal)
def interaction_review_session(
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> ReviewerPrincipal:
    return principal


@app.get("/api/interactions/review/summary", response_model=ReviewSummaryResponse)
def interaction_review_summary(
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> ReviewSummaryResponse:
    return ReviewSummaryResponse.model_validate(interaction_repository.review_summary())


@app.get("/api/interactions/review/{interaction_id}", response_model=RuleDetailResponse)
def interaction_rule_detail(
    interaction_id: str,
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> RuleDetailResponse:
    try:
        return interaction_repository.rule_detail(interaction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="interaction rule not found") from exc


@app.post(
    "/api/interactions/review/{interaction_id}",
    response_model=RuleReviewEvent,
)
def review_interaction_rule(
    interaction_id: str,
    request: AuthenticatedRuleReviewRequest,
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> RuleReviewEvent:
    if request.target_status == ValidationStatus.SOURCE_SPAN_VERIFIED:
        require_role(principal, ReviewerRole.SOURCE_REVIEWER)
    elif request.target_status == ValidationStatus.HUMAN_REVIEWED:
        require_role(principal, ReviewerRole.CLINICAL_REVIEWER)
    elif request.target_status == ValidationStatus.REJECTED:
        if request.expected_status == ValidationStatus.EXTRACTED:
            require_role(principal, ReviewerRole.SOURCE_REVIEWER)
        else:
            require_role(principal, ReviewerRole.CLINICAL_REVIEWER)
    review_request = RuleReviewRequest(
        target_status=request.target_status,
        expected_status=request.expected_status,
        reviewer=principal.reviewer_id,
        note=request.comment,
    )
    try:
        return interaction_repository.review_rule(interaction_id, review_request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="interaction rule not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/api/interactions/review/{interaction_id}/history",
    response_model=list[RuleReviewEvent],
)
def interaction_review_history(
    interaction_id: str,
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> list[RuleReviewEvent]:
    return interaction_repository.review_history(interaction_id)


@app.post(
    "/api/interactions/review/{interaction_id}/notes",
    response_model=RuleReviewEvent,
)
def add_interaction_review_note(
    interaction_id: str,
    request: ReviewNoteRequest,
    principal: ReviewerPrincipal = Depends(require_reviewer),
) -> RuleReviewEvent:
    if request.kind == "correction":
        require_role(principal, ReviewerRole.SOURCE_REVIEWER)
    else:
        require_role(principal, ReviewerRole.CLINICAL_REVIEWER)
    try:
        return interaction_repository.add_review_note(
            interaction_id, request, principal.reviewer_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="interaction rule not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

