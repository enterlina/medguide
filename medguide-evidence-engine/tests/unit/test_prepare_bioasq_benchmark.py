import json
from pathlib import Path

from scripts.prepare_bioasq_benchmark import prepare


def test_selection_and_gold_coverage_are_reproducible(tmp_path: Path) -> None:
    questions = []
    for kind in ("yesno", "factoid", "list", "summary"):
        for index in range(3):
            pmid = f"{len(questions) + 1}"
            questions.append(
                {
                    "id": f"{kind}-{index}",
                    "body": "Q?",
                    "type": kind,
                    "documents": [f"http://www.ncbi.nlm.nih.gov/pubmed/{pmid}"],
                }
            )
    bioasq = tmp_path / "bioasq.json"
    records = tmp_path / "records.jsonl"
    bioasq.write_text(json.dumps({"questions": questions}))
    records.write_text(
        "".join(json.dumps({"pmid": str(i), "abstract": "A"}) + "\n" for i in range(1, 13))
    )
    first = prepare(bioasq, records, seed=7, pilot_size=8)
    second = prepare(bioasq, records, seed=7, pilot_size=8)
    assert first["pilot_questions"] == second["pilot_questions"]
    assert first["summary"]["pilot_by_type"] == {"factoid": 2, "list": 2, "summary": 2, "yesno": 2}
    assert first["summary"]["questions_with_complete_gold_coverage"] == 12
