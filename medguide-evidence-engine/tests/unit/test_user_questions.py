from collections import Counter
from pathlib import Path

from evaluation.dataset import load_golden_candidate_dataset, load_user_question_dataset


DATASET = Path("evaluation/data/user_questions_400.json")


def test_user_question_dataset_is_complete_and_linked() -> None:
    dataset = load_user_question_dataset(DATASET)
    assert len(dataset.supplements) == 100
    assert len(dataset.questions) == 400
    assert set(Counter(question.supplement_id for question in dataset.questions).values()) == {4}


def test_user_questions_are_hypotheses_not_evidence_or_verified_popularity() -> None:
    dataset = load_user_question_dataset(DATASET)
    assert all(question.query_origin == "expert_curated_hypothesis" for question in dataset.questions)
    assert all(not question.popularity_verified for question in dataset.questions)
    assert "Not empirically measured" in dataset.metadata.popularity


def test_each_supplement_covers_four_evaluation_intents() -> None:
    dataset = load_user_question_dataset(DATASET)
    expected = {"effectiveness", "evidence", "dose", "safety_comparison"}
    by_supplement: dict[str, set[str]] = {}
    for question in dataset.questions:
        by_supplement.setdefault(question.supplement_id, set()).add(question.intent)
    assert all(intents == expected for intents in by_supplement.values())


def test_golden_candidates_have_required_diversity_without_fake_labels() -> None:
    dataset = load_golden_candidate_dataset(
        Path("evaluation/data/golden_question_candidates_2000.json")
    )
    assert len(dataset.supplements) == 100
    assert len(dataset.queries) == 2000
    assert sum(query.language != "en" for query in dataset.queries) == 200
    assert sum("typo" in query.challenge_tags for query in dataset.queries) == 200
    assert all(not query.expected_pmids for query in dataset.queries)
    assert all(not query.relevance_labels for query in dataset.queries)
    assert all(query.review_status == "pending_human_review" for query in dataset.queries)

