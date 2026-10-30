#!/usr/bin/env python3
"""Run the curated interaction audit against the real MedGuide HTTP API."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OUTPUT_FILES = (
    "missing_interactions.csv",
    "unsupported_entities.csv",
    "false_positive_warnings.csv",
    "missing_evidence.csv",
)

FINDING_FIELDS = (
    "interactions",
    "timing_restrictions",
    "food_interactions",
    "beverage_interactions",
    "preliminary_findings",
    "label_mentions",
)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def request_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"detail": body}


def flatten_findings(response: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in FINDING_FIELDS:
        for finding in response.get(field, []):
            identifier = finding.get("interaction_id") or stable_hash(finding)
            if identifier not in seen:
                seen.add(identifier)
                findings.append({**finding, "response_bucket": field})
    return findings


def normalized_response(response: dict[str, Any]) -> dict[str, Any]:
    findings = flatten_findings(response)
    return {
        "resolved": [
            {
                "input_name": item.get("input_name"),
                "canonical_names": item.get("canonical_names", []),
                "ingredient_ids": item.get("ingredient_ids", []),
                "resolution": item.get("resolution"),
            }
            for item in response.get("medications", [])
        ],
        "findings": [
            {
                "interaction_id": finding.get("interaction_id"),
                "type": finding.get("interaction_type"),
                "status": finding.get("status"),
                "effect": finding.get("effect"),
                "action": finding.get("recommended_action"),
                "timing": finding.get("timing_rule"),
                "validation_status": finding.get("validation_status"),
                "source_url": (finding.get("source_passage") or {}).get("readable_url")
                or (finding.get("source_passage") or {}).get("source_url"),
                "bucket": finding.get("response_bucket"),
            }
            for finding in findings
        ],
        "duplicates": response.get("duplicate_ingredients", []),
        "coverage_gaps": response.get("coverage_gaps", []),
    }


def grade(case: dict[str, Any], normalized: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unresolved = [item for item in normalized["resolved"] if not item["ingredient_ids"]]
    if unresolved:
        reasons.append("Unresolved inputs: " + ", ".join(item["input_name"] for item in unresolved))
        return "UNSUPPORTED", reasons

    interaction_type = case["interaction_type"]
    findings = normalized["findings"]
    duplicates = normalized["duplicates"]
    if interaction_type == "drug_timing" and case["context"].get("raw"):
        reasons.append("The public request schema has no schedule/context field; pair-level findings only were checked.")
        if not findings:
            return "UNSUPPORTED", reasons

    detected = bool(findings or duplicates)
    if case["must_detect"] and not detected:
        reasons.append("Expected relationship was not returned by any reviewed, preliminary, or label-mention bucket.")
        return ("FAIL" if case["reference_status"] == "verified_anchor" else "NEEDS_HUMAN_REVIEW"), reasons
    if not case["must_detect"] and detected:
        reasons.append("A warning/finding was returned for a negative or qualification control.")
        return ("FAIL" if case["reference_status"] == "verified_anchor" else "NEEDS_HUMAN_REVIEW"), reasons
    if not case["must_detect"]:
        reasons.append("No unsupported finding returned; absence is not interpreted as proof of safety.")
        return ("PASS" if case["reference_status"] == "verified_anchor" else "NEEDS_HUMAN_REVIEW"), reasons

    evidence_present = any(finding.get("source_url") for finding in findings)
    if findings and not evidence_present:
        reasons.append("Finding has no source URL.")
        return "PARTIAL", reasons

    actual_text = " ".join(
        f"{finding.get('effect') or ''} {finding.get('action') or ''}" for finding in findings
    ).lower()
    expected_tokens = {
        token
        for token in re_words(case["expected_effect"])
        if len(token) >= 5 and token not in STOPWORDS
    }
    overlap = sorted(token for token in expected_tokens if token in actual_text)
    if overlap:
        reasons.append("Deterministic semantic token overlap: " + ", ".join(overlap[:8]))
    else:
        reasons.append("Relationship detected, but deterministic text checks could not confirm the expected effect.")
        return "PARTIAL" if case["reference_status"] == "verified_anchor" else "NEEDS_HUMAN_REVIEW", reasons

    missing_qualifiers = [q for q in case["must_include_qualifiers"] if q.lower() not in actual_text]
    if missing_qualifiers:
        reasons.append("Missing qualifiers: " + ", ".join(missing_qualifiers))
        return "PARTIAL", reasons
    if case["reference_status"] == "review_required":
        reasons.append("The reference row is provisional and requires clinician/source review.")
        return "NEEDS_HUMAN_REVIEW", reasons
    return "PASS", reasons


STOPWORDS = {
    "interaction", "identify", "label", "specific", "clinical", "important", "system",
    "should", "result", "source", "detect", "highlight", "merely", "itself", "effect",
}


def re_words(value: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]+", value.lower())


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def app_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--fixture", type=Path, default=Path("tests/fixtures/interaction_gold_v1.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/interactions/audit_v1"))
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    endpoint = args.base_url.rstrip("/") + "/api/interactions/check"
    timestamp = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    resolver_results: list[dict[str, Any]] = []
    for item in fixture.get("resolver_inventory", []):
        payload = {"medications": [{"name": item["name"]}]}
        try:
            http_status, raw = request_json(endpoint, payload, args.timeout)
            medication = (raw.get("medications") or [{}])[0] if isinstance(raw, dict) else {}
            resolved = bool(medication.get("ingredient_ids"))
            status = "RESOLVED" if http_status == 200 and resolved else "UNSUPPORTED"
            reason = medication.get("resolution") or f"HTTP {http_status}"
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raw, status, reason = {"error": str(exc)}, "ERROR", str(exc)
        resolver_results.append(
            {
                **item,
                "status": status,
                "reason": reason,
                "request_sha256": stable_hash(payload),
                "response_sha256": stable_hash(raw),
            }
        )

    for case in fixture["cases"]:
        payload = {"medications": [{"name": item["name"]} for item in case["inputs"]]}
        try:
            http_status, raw = request_json(endpoint, payload, args.timeout)
            if http_status != 200 or not isinstance(raw, dict):
                status, reasons, normalized = "ERROR", [f"HTTP {http_status}"], {}
            else:
                normalized = normalized_response(raw)
                status, reasons = grade(case, normalized)
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raw, normalized, status, reasons = {"error": str(exc)}, {}, "ERROR", [str(exc)]
        results.append(
            {
                "id": case["id"],
                "category": case["interaction_type"],
                "reference_status": case["reference_status"],
                "status": status,
                "reasons": reasons,
                "request": payload,
                "request_sha256": stable_hash(payload),
                "raw_response": raw,
                "response_sha256": stable_hash(raw),
                "normalized_response": normalized,
                "expected_predicates": {
                    key: case[key]
                    for key in (
                        "must_detect", "expected_effect", "expected_action_category",
                        "must_include_qualifiers", "must_not_claim", "evidence_source",
                    )
                },
                "executed_at": timestamp,
            }
        )

    with (args.output_dir / "audit_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    summary_rows = []
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        by_category[result["category"]][result["status"]] += 1
    statuses = ["PASS", "PARTIAL", "FAIL", "UNSUPPORTED", "ERROR", "NEEDS_HUMAN_REVIEW"]
    for category, counts in sorted(by_category.items()):
        summary_rows.append({"category": category, "total": sum(counts.values()), **{s: counts[s] for s in statuses}})
    write_csv(args.output_dir / "audit_summary.csv", summary_rows, ["category", "total", *statuses])

    missing = [r for r in results if r["expected_predicates"]["must_detect"] and r["status"] in {"FAIL", "UNSUPPORTED", "NEEDS_HUMAN_REVIEW"} and not (r.get("normalized_response") or {}).get("findings")]
    false_positive = [r for r in results if not r["expected_predicates"]["must_detect"] and (r.get("normalized_response") or {}).get("findings")]
    missing_evidence = [r for r in results if any(not finding.get("source_url") for finding in (r.get("normalized_response") or {}).get("findings", []))]
    export_sets = {
        "missing_interactions.csv": missing,
        "false_positive_warnings.csv": false_positive,
        "missing_evidence.csv": missing_evidence,
    }
    fields = ["id", "category", "reference_status", "status", "reasons"]
    for filename, rows in export_sets.items():
        write_csv(
            args.output_dir / filename,
            [{**row, "reasons": " | ".join(row["reasons"])} for row in rows],
            fields,
        )
    write_csv(
        args.output_dir / "unsupported_entities.csv",
        [row for row in resolver_results if row["status"] != "RESOLVED"],
        ["group", "category", "name", "status", "reason", "request_sha256", "response_sha256"],
    )

    totals = Counter(result["status"] for result in results)
    resolver_counts = Counter(row["status"] for row in resolver_results)
    priority_missing = sorted(
        missing,
        key=lambda row: (row["reference_status"] != "verified_anchor", row["id"]),
    )
    report = [
        "# MedGuide Interaction Audit v1",
        "",
        f"- Executed: {timestamp}",
        f"- Endpoint: `{endpoint}`",
        f"- Fixture: `{fixture['fixture_version']}` ({len(results)} cases)",
        f"- Resolver inventory: {len(resolver_results)} names; {resolver_counts['RESOLVED']} resolved, {resolver_counts['UNSUPPORTED']} unsupported, {resolver_counts['ERROR']} errors",
        f"- App commit: `{app_commit(Path.cwd())}`",
        "- Safety note: review-required rows are provisional; missing edges never prove safety.",
        "",
        "## Overall results",
        "",
        *[f"- {status}: {totals[status]}" for status in statuses],
        "",
        "## Results by category",
        "",
        "| Category | Total | " + " | ".join(statuses) + " |",
        "|---|---:|" + "---:|" * len(statuses),
    ]
    for row in summary_rows:
        report.append("| " + row["category"] + " | " + str(row["total"]) + " | " + " | ".join(str(row[s]) for s in statuses) + " |")
    report.extend(["", "## Highest-priority gaps", ""])
    for row in priority_missing[:10]:
        source = row["expected_predicates"].get("evidence_source") or "provisional — source review required"
        report.append(f"- **{row['id']}** ({row['status']}): {row['reasons'][0]} Source: {source}")
    report.extend([
        "",
        "## Interpretation limits",
        "",
        "- PASS is only available for deterministic checks against verified-anchor rows.",
        "- NEEDS_HUMAN_REVIEW is intentionally not counted as PASS or FAIL.",
        "- Schedule context is not accepted by the current public API and is reported as unsupported when no pair-level rule exists.",
        "- The runner performs no medication changes and sends only synthetic fixture data.",
    ])
    (args.output_dir / "audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({
        "relationship_cases_executed": len(results),
        "resolver_names_checked": len(resolver_results),
        "resolver_resolved": resolver_counts["RESOLVED"],
        **{status: totals[status] for status in statuses},
    }, indent=2))
    return 1 if totals["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
