from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.models import RuleReviewRequest, ValidationStatus  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


REQUIRED_HEADERS = {
    "Rule ID",
    "Source Match (Pass/Fail)",
    "Clinical Review (Correct/Incorrect/Needs Clarification)",
    "Reviewer Comment",
    "Current Status",
}
REVIEW_VALUES = {"", "Correct", "Incorrect", "Needs Clarification"}


def column_number(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    value = 0
    for character in letters.upper():
        value = value * 26 + ord(character) - ord("A") + 1
    return value


def read_xlsx_tables(path: Path) -> list[dict[str, str]]:
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relationship_namespace = {
        "r": "http://schemas.openxmlformats.org/package/2006/relationships"
    }
    document_relationship = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall("m:si", namespace)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships.findall("r:Relationship", relationship_namespace)
        }
        rows_out: list[dict[str, str]] = []
        for sheet in workbook.findall(".//m:sheet", namespace):
            target = targets[sheet.attrib[document_relationship]].lstrip("/")
            sheet_path = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(archive.read(sheet_path))
            matrix: list[list[str]] = []
            for row in root.findall(".//m:sheetData/m:row", namespace):
                values: dict[int, str] = {}
                for cell in row.findall("m:c", namespace):
                    index = column_number(cell.attrib["r"])
                    cell_type = cell.attrib.get("t")
                    if cell_type == "inlineStr":
                        inline = cell.find("m:is", namespace)
                        value = "".join(inline.itertext()) if inline is not None else ""
                    else:
                        value_node = cell.find("m:v", namespace)
                        raw = value_node.text if value_node is not None and value_node.text else ""
                        value = shared[int(raw)] if cell_type == "s" and raw else raw
                    values[index] = value
                if values:
                    matrix.append([values.get(i, "") for i in range(1, max(values) + 1)])
            if not matrix:
                continue
            header_index = next(
                (index for index, row in enumerate(matrix) if REQUIRED_HEADERS <= set(row)), None
            )
            if header_index is None:
                continue
            headers = matrix[header_index]
            for values in matrix[header_index + 1 :]:
                row = {header: values[index] if index < len(values) else "" for index, header in enumerate(headers)}
                if row.get("Rule ID"):
                    rows_out.append(row)
        return rows_out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate reviewer Excel; dry-run unless --apply and exact confirmation are supplied"
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    rows = read_xlsx_tables(args.workbook)
    if not rows:
        raise ValueError("no review rows found in workbook")
    ids = [row["Rule ID"].strip() for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Rule ID values found across workbook sheets")

    with sqlite3.connect(args.database) as connection:
        connection.row_factory = sqlite3.Row
        database_rows = {
            row["interaction_id"]: row
            for row in connection.execute(
                "SELECT interaction_id, validation_status FROM interaction_rules"
            )
        }
    errors = []
    actions = []
    for number, row in enumerate(rows, 2):
        rule_id = row["Rule ID"].strip()
        decision = row["Clinical Review (Correct/Incorrect/Needs Clarification)"].strip()
        source_match = row["Source Match (Pass/Fail)"].strip()
        comment = row["Reviewer Comment"].strip()
        current = row["Current Status"].strip()
        if decision not in REVIEW_VALUES:
            errors.append(f"row {number}: invalid Clinical Review value")
        if source_match not in {"Pass", "Fail"}:
            errors.append(f"row {number}: Source Match must be Pass or Fail")
        if rule_id not in database_rows:
            errors.append(f"row {number}: unknown Rule ID {rule_id}")
            continue
        actual = database_rows[rule_id]["validation_status"]
        if current != actual:
            errors.append(f"row {number}: stale Current Status for {rule_id}: {current} != {actual}")
        if decision and not comment:
            errors.append(f"row {number}: reviewer comment is required for a decision")
        if decision == "Correct" and source_match != "Pass":
            errors.append(f"row {number}: Correct requires Source Match=Pass")
        if decision in {"Correct", "Incorrect"}:
            actions.append({"rule_id": rule_id, "decision": decision, "status": actual, "comment": comment})
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        raise SystemExit(2)

    preview = {
        "valid": True,
        "rows": len(rows),
        "actions": len(actions),
        "correct": sum(item["decision"] == "Correct" for item in actions),
        "incorrect": sum(item["decision"] == "Incorrect" for item in actions),
        "needs_clarification": sum(
            row["Clinical Review (Correct/Incorrect/Needs Clarification)"].strip()
            == "Needs Clarification"
            for row in rows
        ),
        "apply": args.apply,
    }
    print(json.dumps(preview, indent=2))
    expected_confirmation = f"APPLY {len(actions)}"
    if not args.apply:
        print(f"Dry run only. To apply, add --apply --confirm '{expected_confirmation}'.")
        return
    if args.confirm != expected_confirmation:
        raise ValueError(f"confirmation mismatch; expected: {expected_confirmation}")

    repository = InteractionRepository(args.database)
    for item in actions:
        current = ValidationStatus(item["status"])
        if item["decision"] == "Incorrect":
            repository.review_rule(
                item["rule_id"],
                RuleReviewRequest(
                    target_status=ValidationStatus.REJECTED,
                    expected_status=current,
                    reviewer=args.reviewer,
                    note=item["comment"],
                ),
            )
            continue
        if current == ValidationStatus.EXTRACTED:
            repository.review_rule(
                item["rule_id"],
                RuleReviewRequest(
                    target_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
                    expected_status=current,
                    reviewer=args.reviewer,
                    note=f"Excel review source-span confirmation: {item['comment']}",
                ),
            )
            current = ValidationStatus.SOURCE_SPAN_VERIFIED
        repository.review_rule(
            item["rule_id"],
            RuleReviewRequest(
                target_status=ValidationStatus.HUMAN_REVIEWED,
                expected_status=current,
                reviewer=args.reviewer,
                note=item["comment"],
            ),
        )
    print(json.dumps({"applied": len(actions), "audit_log": "interaction_review_events"}, indent=2))


if __name__ == "__main__":
    main()
