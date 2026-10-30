import json
from pathlib import Path

from scripts.build_bioasq_overlap import build_report, extract_pmid


def test_extract_pmid_accepts_bioasq_pubmed_urls() -> None:
    assert extract_pmid("http://www.ncbi.nlm.nih.gov/pubmed/15858239") == "15858239"
    assert extract_pmid("https://pubmed.ncbi.nlm.nih.gov/33865376/") == "33865376"
    assert extract_pmid("33865376") == "33865376"
    assert extract_pmid("https://example.com/33865376") is None


def test_overlap_is_question_specific(tmp_path: Path) -> None:
    bioasq = tmp_path / "training.json"
    corpus = tmp_path / "corpus.json"
    bioasq.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "id": "q1",
                        "body": "Question?",
                        "type": "summary",
                        "documents": ["http://www.ncbi.nlm.nih.gov/pubmed/123"],
                        "ideal_answer": ["Answer"],
                        "snippets": [
                            {
                                "document": "http://www.ncbi.nlm.nih.gov/pubmed/123",
                                "text": "Evidence",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    corpus.write_text(
        json.dumps([{"identifiers": {"pmid": "123"}}]), encoding="utf-8"
    )

    report = build_report(bioasq, corpus)

    assert report["summary"]["overlapping_pmid_count"] == 1
    assert report["matched_questions"][0]["overlapping_pmids"] == ["123"]
    assert report["matched_questions"][0]["matching_snippets"][0]["text"] == "Evidence"
