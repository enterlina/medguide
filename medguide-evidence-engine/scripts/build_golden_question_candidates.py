from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


SOURCE_DATASET = Path("evaluation/data/user_questions_400.json")
DISCOVERY_LINKS = Path("data/supplements/discovery/supplement_publication_links.json")
OUTPUT = Path("evaluation/data/golden_question_candidates_2000.json")


def typo_name(name: str) -> str:
    normalized = name.lower().replace("’", "").replace("'", "")
    return f"{normalized} suplement"


def templates(supplement: dict) -> list[dict]:
    name = supplement["name"]
    goal = supplement["goal"]
    comparison = supplement["comparison"]
    typo = typo_name(name)
    return [
        {"intent": "effectiveness", "query": f"Does {name} actually {goal}?", "difficulty": "easy"},
        {"intent": "clinical_trials", "query": f"Which randomized controlled trials tested {name} for {goal}?", "difficulty": "medium"},
        {"intent": "systematic_reviews", "query": f"Are there systematic reviews or meta-analyses of {name} for {goal}?", "difficulty": "medium"},
        {"intent": "dose", "query": f"What dose of {name} was studied for {goal}?", "difficulty": "medium"},
        {"intent": "duration", "query": f"How long was {name} used in human studies of {goal}?", "difficulty": "medium"},
        {"intent": "safety", "query": f"What adverse events were reported in human studies of {name}?", "difficulty": "medium"},
        {"intent": "interactions", "query": f"What clinically studied drug interactions are reported for {name}?", "difficulty": "hard"},
        {"intent": "population", "query": f"Has {name} been studied in older adults, children, or pregnant people?", "difficulty": "hard"},
        {"intent": "long_term", "query": f"What is known about long-term safety of {name}?", "difficulty": "hard"},
        {"intent": "null_results", "query": f"Which studies found no statistically significant benefit from {name}?", "difficulty": "hard"},
        {"intent": "formulation", "query": f"Which formulations and routes of {name} were actually tested?", "difficulty": "medium"},
        {"intent": "comparison", "query": f"How does the evidence compare for {comparison}?", "difficulty": "hard"},
        {"intent": "study_quality", "query": f"How strong is the human evidence for {name}, considering study design and risk of bias?", "difficulty": "hard"},
        {"intent": "funding", "query": f"Who funded the main clinical studies of {name}, and was a manufacturer involved?", "difficulty": "hard"},
        {"intent": "multi_study", "query": f"Across all recent human studies, what is consistent and conflicting about {name} for {goal}?", "difficulty": "hard"},
        {"intent": "effectiveness", "query": f"does {typo} really work", "difficulty": "medium", "tags": ["typo", "colloquial"]},
        {"intent": "safety", "query": f"is {typo} safe with my meds", "difficulty": "hard", "tags": ["typo", "colloquial", "incomplete_context"]},
        {"intent": "insufficient_context", "query": "Is this supplement worth taking for me?", "difficulty": "hard", "tags": ["ambiguous", "insufficient_context"]},
        {"intent": "effectiveness", "query": f"Помогает ли {name} для цели «{goal}» и какие есть исследования на людях?", "difficulty": "hard", "language": "ru", "tags": ["multilingual"]},
        {"intent": "safety", "query": f"¿Qué evidencia clínica y riesgos existen para {name}?", "difficulty": "hard", "language": "es", "tags": ["multilingual"]},
    ]


def main() -> None:
    source = json.loads(SOURCE_DATASET.read_text(encoding="utf-8"))
    links = json.loads(DISCOVERY_LINKS.read_text(encoding="utf-8"))
    pmids_by_rank: dict[int, set[str]] = defaultdict(set)
    for link in links:
        pmids_by_rank[int(link["rank"])].add(link["pmid"])
    supplements = source["supplements"]
    questions = []
    for supplement in supplements:
        supplement_id = supplement["supplement_id"]
        rank = int(supplement_id.removeprefix("SUP-"))
        candidates = sorted(pmids_by_rank[rank])
        for index, item in enumerate(templates(supplement), start=1):
            questions.append(
                {
                    "query_id": f"GQ-{supplement_id}-{index:02d}",
                    "supplement_id": supplement_id,
                    "supplement": supplement["name"],
                    "category": supplement["category"],
                    "query": item["query"],
                    "intent": item["intent"],
                    "language": item.get("language", "en"),
                    "difficulty": item["difficulty"],
                    "challenge_tags": item.get("tags", []),
                    "query_context": (
                        {"selected_supplement": supplement["name"]}
                        if "ambiguous" in item.get("tags", [])
                        else {}
                    ),
                    "expected_source_types": ["pubmed", "pmc", "clinicaltrials.gov"],
                    "candidate_pmids": candidates,
                    "expected_pmids": [],
                    "relevance_labels": {},
                    "expected_evidence_facts": [
                        "population",
                        "intervention_form_and_dose",
                        "comparator",
                        "outcomes",
                        "results",
                        "limitations",
                        "funding_and_conflicts",
                    ],
                    "expected_answer_state": "unjudged",
                    "review_status": "pending_human_review",
                }
            )
    payload = {
        "metadata": {
            "version": "2.0-candidate",
            "created_at": datetime.now(UTC).isoformat(),
            "supplement_count": len(supplements),
            "query_count": len(questions),
            "queries_per_supplement": 20,
            "purpose": "Golden-dataset candidates; not valid ground truth until human review.",
            "candidate_pmid_source": str(DISCOVERY_LINKS),
        },
        "supplements": supplements,
        "queries": questions,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["metadata"], indent=2))


if __name__ == "__main__":
    main()
