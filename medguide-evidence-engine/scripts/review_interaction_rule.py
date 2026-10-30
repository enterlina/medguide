from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.interactions.models import RuleReviewRequest, ValidationStatus  # noqa: E402
from app.interactions.repository import InteractionRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit-logged interaction rule review")
    parser.add_argument("interaction_id")
    parser.add_argument(
        "target_status",
        choices=[
            ValidationStatus.SOURCE_SPAN_VERIFIED.value,
            ValidationStatus.HUMAN_REVIEWED.value,
            ValidationStatus.REJECTED.value,
        ],
    )
    parser.add_argument("--expected-status", required=True, choices=[item.value for item in ValidationStatus])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/interactions/interactions.sqlite3"
    )
    args = parser.parse_args()
    event = InteractionRepository(args.database).review_rule(
        args.interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus(args.target_status),
            expected_status=ValidationStatus(args.expected_status),
            reviewer=args.reviewer,
            note=args.note,
        ),
    )
    print(json.dumps(event.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()

