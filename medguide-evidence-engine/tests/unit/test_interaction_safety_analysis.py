from scripts.analyze_interaction_safety import analyze


def row(case_id: str, *, must_detect: bool, findings: list[dict], status: str = "PASS") -> dict:
    return {
        "id": case_id,
        "status": status,
        "expected_predicates": {"must_detect": must_detect},
        "normalized_response": {"findings": findings},
    }


def test_unsupported_cases_are_not_counted_as_correct_abstentions() -> None:
    result = analyze(
        [
            row("positive", must_detect=True, findings=[]),
            row("negative", must_detect=False, findings=[]),
            row("unsupported", must_detect=False, findings=[], status="UNSUPPORTED"),
        ]
    )
    assert result["resolved_case_count"] == 2
    assert result["false_reassurance_proxy_count"] == 1
    assert result["abstention_accuracy_on_resolved_negative_controls"] == 1.0


def test_source_url_coverage_does_not_claim_citation_precision() -> None:
    result = analyze(
        [row("positive", must_detect=True, findings=[{"source_url": "https://example.test"}])]
    )
    assert result["source_url_coverage"] == 1.0
    assert "not citation precision" in result["metric_caveats"]["source_url_coverage"]
