from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
from collections import defaultdict
from pathlib import Path


HEADERS = [
    "Rule ID",
    "Source",
    "Interaction Type",
    "Medication A ID",
    "Medication B / Substance ID",
    "Extracted Effect",
    "Extracted Action",
    "Exact Source Passage",
    "Source URL",
    "Entity Pair Correct (Yes/No/Unclear)",
    "Interaction Type Correct (Yes/No/Unclear)",
    "Effect Supported (Yes/Partial/No/Unclear)",
    "Action Supported (Yes/Partial/No/Unclear)",
    "Should Rule Exist (Yes/No/Unclear)",
    "Reviewer Comment",
]


def sample_rows(database: Path, size: int, seed: int) -> list[dict]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT r.interaction_id, r.interaction_type, r.subject_id, r.object_id,
            r.payload_json, l.source, l.source_url
            FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
            WHERE r.validation_status='extracted' ORDER BY r.interaction_id"""
        ).fetchall()
    strata: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        strata[(row["source"], row["interaction_type"])].append(row)
    rng = random.Random(seed)
    selected: list[sqlite3.Row] = []
    # First cover every source × interaction-type stratum, then fill proportionally
    # from the remaining population. Selection is deterministic for reproducibility.
    for values in strata.values():
        selected.append(rng.choice(values))
    selected_ids = {row["interaction_id"] for row in selected}
    remaining = [row for row in rows if row["interaction_id"] not in selected_ids]
    rng.shuffle(remaining)
    selected.extend(remaining[: max(0, size - len(selected))])
    output = []
    for row in selected[:size]:
        payload = json.loads(row["payload_json"])
        passage = payload["source_passage"]
        output.append(
            {
                "Rule ID": row["interaction_id"],
                "Source": row["source"],
                "Interaction Type": row["interaction_type"],
                "Medication A ID": row["subject_id"],
                "Medication B / Substance ID": row["object_id"],
                "Extracted Effect": payload["effect"],
                "Extracted Action": payload["recommended_action"],
                "Exact Source Passage": passage["text"],
                "Source URL": passage["source_url"],
                "Entity Pair Correct (Yes/No/Unclear)": "",
                "Interaction Type Correct (Yes/No/Unclear)": "",
                "Effect Supported (Yes/Partial/No/Unclear)": "",
                "Action Supported (Yes/Partial/No/Unclear)": "",
                "Should Rule Exist (Yes/No/Unclear)": "",
                "Reviewer Comment": "",
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a deterministic extractor gold sample")
    parser.add_argument("--database", type=Path, default=Path("data/interactions/interactions.sqlite3"))
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation/data/interaction_extractor_gold_sample_200.csv")
    )
    args = parser.parse_args()
    rows = sample_rows(args.database, args.size, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    protocol = args.output.with_suffix(".md")
    protocol.write_text(
        "\n".join(
            [
                "# Interaction extractor gold-sample protocol",
                "",
                f"This file contains **{len(rows)}** deterministic, stratified candidates.",
                "It is an annotation set, not ground truth until reviewed.",
                "",
                "## Annotation rules",
                "",
                "1. Read the exact passage and open the source when context is truncated.",
                "2. Judge the entity pair separately from the effect and action.",
                "3. Use `Unclear` instead of guessing; it is not counted as negative.",
                "4. `Should Rule Exist=No` means the passage should not produce this interaction rule.",
                "5. A second reviewer should independently label at least 20% to measure agreement.",
                "",
                "## Metrics after annotation",
                "",
                "- Candidate precision: `Should Rule Exist=Yes / (Yes + No)`; exclude Unclear.",
                "- Entity-pair accuracy, type accuracy, effect support, and action support are reported separately.",
                "- Recall/F1 require additional negative source passages; this candidate-only sheet cannot measure recall.",
                "- Report reviewer agreement (Cohen's kappa or weighted kappa) before resolving disagreements.",
                "",
            ]
        )
        + "\n"
    )
    print(json.dumps({"rows": len(rows), "csv": str(args.output), "protocol": str(protocol)}, indent=2))


if __name__ == "__main__":
    main()
