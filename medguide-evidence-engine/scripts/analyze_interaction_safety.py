from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def analyze(rows: list[dict]) -> dict:
    resolved = [row for row in rows if row["status"] != "UNSUPPORTED"]
    must_detect = [row for row in resolved if row["expected_predicates"]["must_detect"]]
    negative = [row for row in resolved if not row["expected_predicates"]["must_detect"]]
    missed = [
        row
        for row in must_detect
        if not (row.get("normalized_response") or {}).get("findings")
    ]
    negative_with_warning = [
        row
        for row in negative
        if (row.get("normalized_response") or {}).get("findings")
    ]
    findings = [
        finding
        for row in resolved
        for finding in (row.get("normalized_response") or {}).get("findings", [])
    ]
    cited = [finding for finding in findings if finding.get("source_url")]
    return {
        "case_count": len(rows),
        "resolved_case_count": len(resolved),
        "unsupported_case_count": len(rows) - len(resolved),
        "coverage_rate": len(resolved) / len(rows) if rows else 0.0,
        "status_distribution": dict(Counter(row["status"] for row in rows)),
        "resolved_must_detect_cases": len(must_detect),
        "resolved_must_detect_with_any_finding": len(must_detect) - len(missed),
        "finding_recall_on_resolved_must_detect": (
            (len(must_detect) - len(missed)) / len(must_detect) if must_detect else None
        ),
        "false_reassurance_proxy_count": len(missed),
        "false_reassurance_proxy_rate": len(missed) / len(must_detect) if must_detect else None,
        "false_reassurance_case_ids": [row["id"] for row in missed],
        "resolved_negative_controls": len(negative),
        "negative_controls_with_warning": len(negative_with_warning),
        "abstention_accuracy_on_resolved_negative_controls": (
            (len(negative) - len(negative_with_warning)) / len(negative) if negative else None
        ),
        "returned_findings": len(findings),
        "findings_with_source_url": len(cited),
        "source_url_coverage": len(cited) / len(findings) if findings else None,
        "metric_caveats": {
            "false_reassurance_proxy": (
                "A resolved must-detect test with no returned finding. It measures a dangerous "
                "system behavior, but is not a clinically adjudicated population rate."
            ),
            "source_url_coverage": (
                "Presence of a URL is not citation precision. Citation precision requires a human "
                "judgment that the cited passage supports the displayed claim."
            ),
            "unsupported": "Unsupported cases are excluded from conditional performance rates and reported separately.",
        },
    }


def report(result: dict) -> str:
    def percentage(value: float | None) -> str:
        return "unavailable" if value is None else f"{value:.1%}"

    return "\n".join(
        [
            "# Interaction safety evaluation",
            "",
            f"- Cases: **{result['case_count']}**",
            f"- Resolver/API coverage: **{result['resolved_case_count']}/{result['case_count']} "
            f"({result['coverage_rate']:.1%})**",
            f"- Finding recall among resolved must-detect cases: "
            f"**{percentage(result['finding_recall_on_resolved_must_detect'])}**",
            f"- False-reassurance proxy: **{result['false_reassurance_proxy_count']}/"
            f"{result['resolved_must_detect_cases']} "
            f"({percentage(result['false_reassurance_proxy_rate'])})**",
            f"- Abstention accuracy on resolved negative controls: "
            f"**{percentage(result['abstention_accuracy_on_resolved_negative_controls'])}**",
            f"- Returned findings with a source URL: **{result['findings_with_source_url']}/"
            f"{result['returned_findings']} ({percentage(result['source_url_coverage'])})**",
            "",
            "## False-reassurance proxy cases",
            "",
            *(f"- {case_id}" for case_id in result["false_reassurance_case_ids"]),
            "",
            "## Interpretation",
            "",
            "Unsupported cases are a coverage failure, not a correct abstention and not proof of safety.",
            "A source URL proves neither citation correctness nor clinical correctness. Those require passage-level human review.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=Path("artifacts/interactions/audit_v1/audit_results.jsonl")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/interactions/audit_v1/safety_metrics.json")
    )
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line]
    result = analyze(rows)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(report(result) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
