#!/usr/bin/env python3
"""AI-screen PubMed entity matches without promoting them to human-reviewed evidence."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


DEFAULT_LINKS = Path("data/catalog/discovery/entity_publication_links.json")
DEFAULT_ARTICLES = Path("data/catalog/discovery/pubmed_recent.json")
DEFAULT_OUTPUT = Path("artifacts/evidence-review/openai_screening_v2.jsonl")
DEFAULT_SUMMARY = Path("artifacts/evidence-review/openai_screening_v2.summary.json")


class ModelAssessment(BaseModel):
    entity_match: Literal[
        "exact", "related_form", "incidental_mention", "wrong", "unclear"
    ]
    study_role: Literal[
        "primary_intervention",
        "comparator",
        "background",
        "rescue_medication",
        "mentioned_only",
        "unclear",
    ]
    outcome_match: Literal["direct", "indirect", "not_measured", "unclear"]
    effect_attribution: Literal[
        "isolated", "combination_only", "shared_both_arms", "not_applicable", "unclear"
    ]
    proposed_decision: Literal["include", "include_as_indirect", "exclude", "needs_review"]
    confidence: Literal["high", "medium", "low"]
    evidence_quotes: list[str] = Field(min_length=1, max_length=3)
    reason: str = Field(min_length=1, max_length=500)


SYSTEM_PROMPT = """You screen biomedical search matches for MedGuide.
Evaluate only the supplied entity, title, publication types, and abstract. Do not use outside
knowledge. The mere presence of an entity name is not enough. A rescue medication, background
mention, list item, or incidental comparator is not direct evidence about that entity. Direct
evidence requires that the entity (or a clearly related form) is an intervention/exposure or an
explicitly evaluated comparator and that the study measures outcomes for it.

Separately classify effect attribution. Use isolated only when the reported comparison can
attribute an outcome to the entity itself. Use combination_only when the entity is evaluated only
inside a multi-ingredient or multi-drug regimen. Use shared_both_arms when the entity is present in
both compared groups, so the difference cannot be attributed to it. Combination-only and
shared-both-arms evidence must not be proposed as direct include evidence.

Return exact, verbatim evidence quotes copied from the supplied title or abstract. Propose:
- include: direct evidence about the requested entity;
- include_as_indirect: useful but related-form, comparator, or indirect evidence;
- exclude: wrong entity, incidental/background/rescue mention, or no measured entity outcome;
- needs_review: genuinely ambiguous from the supplied text.
Never treat missing information as negative evidence."""


def load_work(links_path: Path, articles_path: Path) -> list[dict]:
    links = json.loads(links_path.read_text(encoding="utf-8"))
    articles = {
        str(row["pmid"]): row
        for row in json.loads(articles_path.read_text(encoding="utf-8"))
    }
    work = []
    for link in links:
        article = articles.get(str(link["pmid"]))
        if article is None:
            raise ValueError(f"Missing article for PMID {link['pmid']}")
        work.append({"link": link, "article": article})
    return work


def key_for(link: dict) -> str:
    return f"{link['entity_id']}::{link['pmid']}"


def validate_and_finalize(assessment: ModelAssessment, source_text: str) -> dict:
    valid_quotes = [quote for quote in assessment.evidence_quotes if quote in source_text]
    validation_errors = []
    if len(valid_quotes) != len(assessment.evidence_quotes):
        validation_errors.append("one_or_more_quotes_not_found_verbatim")

    incidental_roles = {"background", "rescue_medication", "mentioned_only"}
    if assessment.entity_match in {"incidental_mention", "wrong"}:
        decision = "exclude"
    elif assessment.study_role in incidental_roles:
        decision = "exclude"
    elif assessment.outcome_match == "not_measured":
        decision = "exclude"
    elif assessment.effect_attribution in {"combination_only", "shared_both_arms"}:
        decision = "include_as_indirect"
    elif (
        assessment.entity_match == "exact"
        and assessment.study_role == "primary_intervention"
        and assessment.outcome_match == "direct"
        and assessment.effect_attribution == "isolated"
        and assessment.confidence == "high"
    ):
        decision = "include"
    elif assessment.proposed_decision == "exclude" and assessment.confidence != "low":
        decision = "exclude"
    elif assessment.confidence != "low" and assessment.proposed_decision in {
        "include",
        "include_as_indirect",
    }:
        decision = "include_as_indirect"
    else:
        decision = "needs_review"

    confidence = assessment.confidence
    if validation_errors or not valid_quotes:
        decision = "needs_review"
        confidence = "low"
    return {
        **assessment.model_dump(),
        "decision": decision,
        "confidence": confidence,
        "evidence_quotes": valid_quotes,
        "validation_errors": validation_errors,
    }


def read_completed(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    completed = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            completed[row["screening_key"]] = row
    return completed


def write_summary(path: Path, rows: list[dict], total: int, model: str) -> None:
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model,
        "total_matches": total,
        "screened_matches": len(rows),
        "decisions": dict(Counter(row["decision"] for row in rows)),
        "confidence": dict(Counter(row["confidence"] for row in rows)),
        "human_reviewed": 0,
        "policy": "AI screening only; no automatic promotion to human-reviewed evidence.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--model", default=os.getenv("OPENAI_SCREENING_MODEL", "gpt-6.1-sol"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    work = load_work(args.links, args.articles)
    completed = read_completed(args.output)
    pending = [item for item in work if key_for(item["link"]) not in completed]
    if args.limit is not None:
        pending = pending[: args.limit]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "total_matches": len(work),
                    "already_screened": len(completed),
                    "pending_this_run": len(pending),
                    "model": args.model,
                    "output": str(args.output),
                },
                indent=2,
            )
        )
        return
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required. Add it locally; do not paste it into chat.")

    from openai import OpenAI

    client = OpenAI()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as output:
        for index, item in enumerate(pending, 1):
            link = item["link"]
            article = item["article"]
            payload = {
                "entity": {
                    "id": link["entity_id"],
                    "name": link["name"],
                    "type": link["entity_type"],
                },
                "article": {
                    "pmid": str(article["pmid"]),
                    "title": article.get("title", ""),
                    "publication_types": article.get("publication_types", []),
                    "abstract": article.get("abstract", ""),
                },
            }
            response = client.responses.parse(
                model=args.model,
                instructions=SYSTEM_PROMPT,
                input=json.dumps(payload, ensure_ascii=False),
                text_format=ModelAssessment,
                store=False,
            )
            if response.output_parsed is None:
                raise RuntimeError(f"No parsed output for {key_for(link)}")
            source_text = f"{article.get('title', '')}\n{article.get('abstract', '')}"
            final = validate_and_finalize(response.output_parsed, source_text)
            row = {
                "screening_key": key_for(link),
                "entity_id": link["entity_id"],
                "entity_name": link["name"],
                "pmid": str(link["pmid"]),
                "title": article.get("title", ""),
                "source_url": article.get("source_url"),
                "model": args.model,
                "screened_at": datetime.now(UTC).isoformat(),
                **final,
            }
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            completed[row["screening_key"]] = row
            print(f"[{index}/{len(pending)}] {row['screening_key']}: {row['decision']}")

    rows = list(completed.values())
    write_summary(args.summary, rows, len(work), args.model)
    print(f"Saved {len(rows)} AI-screened matches to {args.output}")


if __name__ == "__main__":
    main()
