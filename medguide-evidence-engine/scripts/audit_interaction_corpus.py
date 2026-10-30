from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.models import InteractionRule  # noqa: E402


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def audit(database: Path) -> tuple[dict, list[dict]]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT r.interaction_id, r.validation_status, r.payload_json,
            l.source, l.source_url, l.sections_json
            FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
            ORDER BY r.interaction_id"""
        ).fetchall()
    details: list[dict] = []
    groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for row in rows:
        rule = InteractionRule.model_validate_json(row["payload_json"])
        sections = json.loads(row["sections_json"])
        blocks = sections.get(rule.source_passage.section) or []
        exact_match = any(rule.source_passage.text in str(block) for block in blocks)
        signature = (
            rule.subject_id,
            rule.object_id,
            rule.interaction_type.value,
            normalized(rule.effect),
            normalized(rule.recommended_action),
            normalized(rule.source_passage.text),
        )
        groups[signature].append(rule.interaction_id)
        details.append(
            {
                "interaction_id": rule.interaction_id,
                "review_status": row["validation_status"],
                "interaction_type": rule.interaction_type.value,
                "subject_id": rule.subject_id,
                "object_id": rule.object_id,
                "source": row["source"],
                "source_url": row["source_url"],
                "source_section": rule.source_passage.section,
                "source_span_exact_match": exact_match,
                "duplicate_group_size": 0,
            }
        )
    sizes = {identifier: len(ids) for ids in groups.values() for identifier in ids}
    for row in details:
        row["duplicate_group_size"] = sizes[row["interaction_id"]]
    exact = sum(row["source_span_exact_match"] for row in details)
    duplicate_groups = [ids for ids in groups.values() if len(ids) > 1]
    summary = {
        "database": str(database),
        "read_only": True,
        "review_status_changed": False,
        "important_semantics": (
            "source_span_exact_match verifies provenance only. It does not verify clinical "
            "interpretation and does not promote source_span_verified or human_reviewed status."
        ),
        "rules_total": len(details),
        "source_span_exact_match": exact,
        "source_span_exact_match_rate": exact / len(details) if details else 0.0,
        "source_span_mismatch": len(details) - exact,
        "unique_rule_signatures": len(groups),
        "duplicate_groups": len(duplicate_groups),
        "rules_in_duplicate_groups": sum(len(ids) for ids in duplicate_groups),
        "review_status_distribution": dict(Counter(row["review_status"] for row in details)),
        "interaction_type_distribution": dict(Counter(row["interaction_type"] for row in details)),
        "source_distribution": dict(Counter(row["source"] for row in details)),
    }
    return summary, details


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only provenance audit for every interaction rule")
    parser.add_argument("--database", type=Path, default=Path("data/interactions/interactions.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/interactions/corpus_audit"))
    args = parser.parse_args()
    summary, details = audit(args.database)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (args.output / "rules.jsonl").open("w") as handle:
        for row in details:
            handle.write(json.dumps(row) + "\n")
    (args.output / "report.md").write_text(
        "\n".join(
            [
                "# Interaction corpus provenance audit",
                "",
                "This audit is read-only and covers every stored rule.",
                "",
                f"- Rules: **{summary['rules_total']:,}**",
                f"- Exact stored-source span matches: **{summary['source_span_exact_match']:,}** "
                f"({summary['source_span_exact_match_rate']:.1%})",
                f"- Source span mismatches: **{summary['source_span_mismatch']:,}**",
                f"- Deduplicated signatures: **{summary['unique_rule_signatures']:,}**",
                f"- Duplicate groups: **{summary['duplicate_groups']:,}**",
                f"- Rules in duplicate groups: **{summary['rules_in_duplicate_groups']:,}**",
                "",
                "## Critical interpretation",
                "",
                summary["important_semantics"],
                "",
                "Exact matching demonstrates that the quoted text came from the stored label. "
                "It does not demonstrate that the extractor interpreted the passage correctly.",
                "",
            ]
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
