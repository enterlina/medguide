import json
import subprocess
import sys
from pathlib import Path


def test_question_coverage_report_is_complete_and_conservative(tmp_path: Path) -> None:
    output = tmp_path / "coverage.json"
    markdown = tmp_path / "coverage.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_question_coverage.py",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["questions"]) == 400
    assert sum(report["summary"]["coverage_statuses"].values()) == 400
    assert all(not row["human_reviewed"] for row in report["questions"])
    assert all(
        row["coverage_status"] == "insufficient_discovery_evidence"
        for row in report["questions"]
        if not row["candidate_pmids"]
    )
    assert markdown.exists()
