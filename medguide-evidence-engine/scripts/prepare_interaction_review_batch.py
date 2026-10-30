from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.catalog import IngredientCatalog  # noqa: E402
from app.interactions.models import InteractionRule, ValidationStatus  # noqa: E402


REVIEW_HEADERS = [
    "Rule ID",
    "Medication A",
    "Medication B / Substance",
    "Interaction Type",
    "Severity",
    "Clinical Effect",
    "Recommended Action",
    "Timing Interval",
    "Official Source",
    "Exact Source Passage",
    "Source Match (Pass/Fail)",
    "Clinical Review (Correct/Incorrect/Needs Clarification)",
    "Reviewer Comment",
    "Current Status",
    "Potentially Serious",
    "Duplicate Group",
    "Machine Issues",
]


def reviewer_group(rule: InteractionRule) -> str:
    value = rule.interaction_type.value
    if value == "timing_separation":
        return "Timing"
    if value == "drug_food":
        return "Food"
    if value == "drug_beverage":
        return "Beverages"
    return "Drug–Drug"


def display_name(identifier: str, catalog: IngredientCatalog) -> str:
    ingredient = catalog.ingredients.get(identifier)
    if ingredient:
        return ingredient.canonical_name
    return identifier.removeprefix("substance:").replace("-", " ")


def timing_display(rule: InteractionRule) -> str:
    timing = rule.timing_rule
    if timing is None:
        return ""
    interval = (
        f"{timing.minimum_interval_minutes} minutes"
        if timing.minimum_interval_minutes is not None
        else "Interval not stated"
    )
    return f"{interval}; {timing.direction.value}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only interaction rule audit and export")
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "data/interactions/pilot_ingredients.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/interactions/review_batch_001"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    catalog = IngredientCatalog.from_json(args.catalog)

    with sqlite3.connect(args.database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT r.payload_json, l.source, l.sections_json
            FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
            WHERE r.validation_status=? ORDER BY r.interaction_type, r.subject_id, r.object_id,
            r.interaction_id""",
            (ValidationStatus.EXTRACTED.value,),
        ).fetchall()

    audited = []
    signatures: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for row in rows:
        rule = InteractionRule.model_validate_json(row["payload_json"])
        sections = json.loads(row["sections_json"])
        blocks = sections.get(rule.source_passage.section, [])
        source_match = any(rule.source_passage.text in block for block in blocks)
        signature = (
            rule.subject_id,
            rule.object_id,
            rule.interaction_type.value,
            rule.status.value,
            " ".join(rule.source_passage.text.casefold().split()),
        )
        signatures[signature].append(rule.interaction_id)
        issues = []
        if not source_match:
            issues.append("Exact source passage not found in stored label section")
        if rule.severity is None:
            issues.append("Severity not extracted")
        if rule.effect.strip() == rule.recommended_action.strip():
            issues.append("Clinical effect and recommended action are identical")
        if len(rule.source_passage.text) > 800:
            issues.append("Long source passage requires segmentation review")
        audited.append(
            {
                "rule": rule,
                "source": row["source"],
                "source_match": source_match,
                "issues": issues,
                "signature": signature,
            }
        )

    duplicate_groups = {
        signature: f"DUP-{number:03d}"
        for number, (signature, ids) in enumerate(
            ((signature, ids) for signature, ids in signatures.items() if len(ids) > 1), 1
        )
    }
    export_rows = []
    for item in audited:
        rule = item["rule"]
        serious = rule.status.value in {"CONTRAINDICATED", "AVOID_COMBINATION"}
        duplicate_group = duplicate_groups.get(item["signature"], "")
        issues = list(item["issues"])
        if duplicate_group:
            issues.append(f"Potential duplicate in {duplicate_group}")
        export_rows.append(
            {
                "Rule ID": rule.interaction_id,
                "Medication A": display_name(rule.subject_id, catalog),
                "Medication B / Substance": display_name(rule.object_id, catalog),
                "Interaction Type": reviewer_group(rule),
                "Severity": rule.severity or "Not extracted",
                "Clinical Effect": rule.effect,
                "Recommended Action": rule.recommended_action,
                "Timing Interval": timing_display(rule),
                "Official Source": str(rule.source_passage.source_url),
                "Exact Source Passage": rule.source_passage.text,
                "Source Match (Pass/Fail)": "Pass" if item["source_match"] else "Fail",
                "Clinical Review (Correct/Incorrect/Needs Clarification)": "",
                "Reviewer Comment": "",
                "Current Status": rule.validation_status.value,
                "Potentially Serious": "Yes" if serious else "No",
                "Duplicate Group": duplicate_group,
                "Machine Issues": "; ".join(issues),
            }
        )

    csv_path = args.output / "interaction_review_batch_001.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_HEADERS)
        writer.writeheader()
        writer.writerows(export_rows)
    grouped_outputs = {}
    for group in ("Drug–Drug", "Timing", "Food", "Beverages"):
        safe_name = group.replace("–", "_").replace(" ", "_").casefold()
        group_path = args.output / f"{safe_name}.csv"
        with group_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=REVIEW_HEADERS)
            writer.writeheader()
            writer.writerows(row for row in export_rows if row["Interaction Type"] == group)
        grouped_outputs[group] = str(group_path)
    serious_path = args.output / "potentially_serious.csv"
    with serious_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_HEADERS)
        writer.writeheader()
        writer.writerows(row for row in export_rows if row["Potentially Serious"] == "Yes")

    distribution = Counter(row["Interaction Type"] for row in export_rows)
    raw_types = Counter(item["rule"].interaction_type.value for item in audited)
    status_distribution = Counter(item["rule"].status.value for item in audited)
    problem_counts = Counter(issue for item in audited for issue in item["issues"])
    report = {
        "batch_id": "interaction-review-batch-001",
        "database": str(args.database),
        "read_only": True,
        "review_status_changed": False,
        "rule_count": len(export_rows),
        "source_match_pass": sum(row["Source Match (Pass/Fail)"] == "Pass" for row in export_rows),
        "source_match_fail": sum(row["Source Match (Pass/Fail)"] == "Fail" for row in export_rows),
        "reviewer_group_distribution": dict(distribution),
        "raw_interaction_type_distribution": dict(raw_types),
        "interaction_status_distribution": dict(status_distribution),
        "potentially_serious_count": sum(row["Potentially Serious"] == "Yes" for row in export_rows),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_rule_count": sum(len(ids) for ids in signatures.values() if len(ids) > 1),
        "problem_counts": dict(problem_counts),
        "outputs": {
            "csv": str(csv_path),
            "groups": grouped_outputs,
            "potentially_serious": str(serious_path),
        },
    }
    report_path = args.output / "machine_validation_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path = args.output / "machine_validation_report.md"
    markdown_path.write_text(
        "\n".join(
            [
                "# MedGuide Interaction Corpus — Machine Validation Batch 001",
                "",
                "This audit is read-only. No review status was changed.",
                "",
                f"- Extracted rules: **{report['rule_count']}**",
                f"- Exact source passage matches: **{report['source_match_pass']}**",
                f"- Failed source matches: **{report['source_match_fail']}**",
                f"- Potentially serious candidates: **{report['potentially_serious_count']}**",
                f"- Duplicate groups: **{report['duplicate_group_count']}** ",
                f"- Rules participating in duplicate groups: **{report['duplicate_rule_count']}**",
                "",
                "## Reviewer groups",
                "",
                *[
                    f"- {name}: {count}"
                    for name, count in report["reviewer_group_distribution"].items()
                ],
                "",
                "## Machine-detected issues",
                "",
                *[f"- {name}: {count}" for name, count in report["problem_counts"].items()],
                "",
                "Clinical correctness was not inferred from source matching. Exact provenance,",
                "clinical interpretation, applicability, severity, and recommended action remain",
                "separate review decisions.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    report["outputs"]["markdown_report"] = str(markdown_path)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "review_rows.json").write_text(
        json.dumps(export_rows, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
