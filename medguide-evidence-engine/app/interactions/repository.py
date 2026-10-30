from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.interactions.models import (
    Ingredient,
    InteractionRule,
    LabelDocument,
    LabelSectionPreview,
    MedicationLabelGuidance,
    RuleReviewEvent,
    ReviewNoteRequest,
    RuleReviewRequest,
    RuleDetailResponse,
    ValidationStatus,
)


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS ingredients(
  ingredient_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, rxcui TEXT,
  aliases_json TEXT NOT NULL, ingredient_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS labels(
  label_id TEXT PRIMARY KEY, source TEXT NOT NULL, source_url TEXT NOT NULL,
  set_id TEXT, version TEXT, effective_time TEXT, product_name TEXT, rxcui TEXT,
  ingredient_ids_json TEXT NOT NULL, sections_json TEXT NOT NULL, content_hash TEXT NOT NULL,
  UNIQUE(source, set_id, version, content_hash)
);
CREATE TABLE IF NOT EXISTS interaction_rules(
  interaction_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, object_id TEXT NOT NULL,
  interaction_type TEXT NOT NULL, status TEXT NOT NULL, validation_status TEXT NOT NULL,
  payload_json TEXT NOT NULL, label_id TEXT NOT NULL REFERENCES labels(label_id)
);
CREATE INDEX IF NOT EXISTS interaction_pair_idx ON interaction_rules(subject_id, object_id);
CREATE TABLE IF NOT EXISTS interaction_review_events(
  event_id TEXT PRIMARY KEY, interaction_id TEXT NOT NULL REFERENCES interaction_rules(interaction_id),
  previous_status TEXT NOT NULL, new_status TEXT NOT NULL, reviewer TEXT NOT NULL,
  note TEXT NOT NULL, reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS interaction_review_rule_idx
  ON interaction_review_events(interaction_id, reviewed_at);
"""


class InteractionRepository:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def upsert_ingredients(self, ingredients: list[Ingredient]) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO ingredients VALUES(?,?,?,?,?) ON CONFLICT(ingredient_id) DO UPDATE SET
                canonical_name=excluded.canonical_name, rxcui=COALESCE(excluded.rxcui,ingredients.rxcui),
                aliases_json=excluded.aliases_json, ingredient_kind=excluded.ingredient_kind""",
                [
                    (
                        item.ingredient_id,
                        item.canonical_name,
                        item.rxcui,
                        json.dumps(item.aliases),
                        item.ingredient_kind,
                    )
                    for item in ingredients
                ],
            )

    def store_label_and_rules(self, label: LabelDocument, rules: list[InteractionRule]) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO labels VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(label_id) DO UPDATE SET
                source_url=excluded.source_url, version=excluded.version, effective_time=excluded.effective_time,
                ingredient_ids_json=excluded.ingredient_ids_json, sections_json=excluded.sections_json,
                content_hash=excluded.content_hash""",
                (
                    label.label_id,
                    label.source,
                    str(label.source_url),
                    label.set_id,
                    label.version,
                    label.effective_time,
                    label.product_name,
                    label.rxcui,
                    json.dumps(label.ingredient_ids),
                    json.dumps(label.sections),
                    label.content_hash,
                ),
            )
            # A repeat extraction replaces machine candidates for this label while preserving
            # human-reviewed rules. This prevents stale rules after parser/extractor changes.
            connection.execute(
                "DELETE FROM interaction_rules WHERE label_id=? AND validation_status='extracted'",
                (label.label_id,),
            )
            connection.executemany(
                """INSERT INTO interaction_rules VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(interaction_id) DO UPDATE SET
                payload_json=CASE
                  WHEN interaction_rules.validation_status='extracted' THEN excluded.payload_json
                  ELSE interaction_rules.payload_json
                END,
                validation_status=interaction_rules.validation_status""",
                [
                    (
                        rule.interaction_id,
                        rule.subject_id,
                        rule.object_id,
                        rule.interaction_type.value,
                        rule.status.value,
                        rule.validation_status.value,
                        rule.model_dump_json(),
                        label.label_id,
                    )
                    for rule in rules
                ],
            )

    def find_rules(self, ingredient_ids: list[str]) -> list[InteractionRule]:
        if not ingredient_ids or not self.path.exists():
            return []
        placeholders = ",".join("?" for _ in ingredient_ids)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT payload_json FROM interaction_rules
                WHERE subject_id IN ({placeholders}) OR object_id IN ({placeholders})""",
                [*ingredient_ids, *ingredient_ids],
            ).fetchall()
        return [InteractionRule.model_validate_json(row["payload_json"]) for row in rows]

    def covered_ingredients(self) -> set[str]:
        if not self.path.exists():
            return set()
        with self.connect() as connection:
            rows = connection.execute("SELECT ingredient_ids_json FROM labels").fetchall()
        return {item for row in rows for item in json.loads(row[0])}

    def readable_source_urls(self, label_ids: list[str]) -> dict[str, str]:
        if not label_ids or not self.path.exists():
            return {}
        placeholders = ",".join("?" for _ in label_ids)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT label_id, source_url, set_id FROM labels WHERE label_id IN ({placeholders})",
                label_ids,
            ).fetchall()
        return {
            row["label_id"]: (
                f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={row['set_id']}"
                if row["set_id"]
                else row["source_url"]
            )
            for row in rows
        }

    def label_guidance(
        self, ingredient_ids: list[str], set_ids: list[str] | None = None
    ) -> list[MedicationLabelGuidance]:
        if not ingredient_ids or not self.path.exists():
            return []
        placeholders = ",".join("?" for _ in ingredient_ids)
        set_filter = ""
        parameters: list[str] = list(ingredient_ids)
        if set_ids:
            set_placeholders = ",".join("?" for _ in set_ids)
            set_filter = f" AND l.set_id IN ({set_placeholders})"
            parameters.extend(set_ids)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT DISTINCT l.* FROM labels l, json_each(l.ingredient_ids_json) item
                WHERE item.value IN ({placeholders}){set_filter} ORDER BY l.source, l.label_id""",
                parameters,
            ).fetchall()
        priority = (
            "interactions_with_medications",
            "health_risks_from_excessive_vitamin_d",
            "recommended_intakes",
            "dosage_and_administration",
            "instructions_for_use",
            "information_for_patients",
            "indications_and_usage",
            "drug_interactions",
            "contraindications",
            "adverse_reactions",
            "warnings_and_precautions",
            "warnings_and_cautions",
            "warnings",
            "precautions",
            "ask_doctor_or_pharmacist",
            "do_not_use",
            "pregnancy",
            "lactation",
            "pediatric_use",
            "geriatric_use",
            "use_in_specific_populations",
        )
        guidance: list[MedicationLabelGuidance] = []
        for row in rows:
            sections = json.loads(row["sections_json"])
            previews = []
            for section in priority:
                blocks = sections.get(section) or []
                if not blocks:
                    continue
                selected_blocks = blocks[:8] if row["source"] == "nih_ods" else blocks[:1]
                for block in selected_blocks:
                    passage = " ".join(str(block).split())
                    limit = 700
                    previews.append(
                        LabelSectionPreview(
                            section=section,
                            passage=passage[:limit].rstrip(),
                            excerpted=len(passage) > limit,
                        )
                    )
            if not previews:
                continue
            ingredient_values = json.loads(row["ingredient_ids_json"])
            ingredient_id = next(
                (item for item in ingredient_values if item in ingredient_ids),
                ingredient_values[0],
            )
            readable_url = (
                f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={row['set_id']}"
                if row["set_id"]
                else row["source_url"]
            )
            guidance.append(
                MedicationLabelGuidance(
                    ingredient_id=ingredient_id,
                    source_name=row["source"],
                    product_name=row["product_name"],
                    document_version=row["version"],
                    source_url=readable_url,
                    sections=previews,
                )
            )
        return guidance

    def review_queue(
        self,
        status: ValidationStatus,
        limit: int = 50,
        offset: int = 0,
        interaction_type: str | None = None,
    ) -> tuple[list[InteractionRule], int]:
        self.initialize()
        where = "validation_status=?"
        parameters: list[object] = [status.value]
        if interaction_type:
            where += " AND interaction_type=?"
            parameters.append(interaction_type)
        with self.connect() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM interaction_rules WHERE {where}",
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""SELECT payload_json FROM interaction_rules WHERE {where}
                ORDER BY label_id, interaction_id LIMIT ? OFFSET ?""",
                [*parameters, limit, offset],
            ).fetchall()
        return [InteractionRule.model_validate_json(row[0]) for row in rows], total

    def review_summary(self) -> dict[str, int]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT validation_status, COUNT(*) count FROM interaction_rules GROUP BY validation_status"
            ).fetchall()
        counts = {status.value: 0 for status in ValidationStatus}
        counts.update({row["validation_status"]: int(row["count"]) for row in rows})
        return counts

    def rule_detail(self, interaction_id: str) -> RuleDetailResponse:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                """SELECT r.payload_json, l.source, l.version, l.set_id, l.product_name,
                l.sections_json FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
                WHERE r.interaction_id=?""",
                (interaction_id,),
            ).fetchone()
        if row is None:
            raise KeyError(interaction_id)
        rule = InteractionRule.model_validate_json(row["payload_json"])
        sections = json.loads(row["sections_json"])
        source_match = any(
            rule.source_passage.text in block
            for block in sections.get(rule.source_passage.section, [])
        )
        return RuleDetailResponse(
            rule=rule,
            source_name=row["source"],
            document_version=row["version"],
            set_id=row["set_id"],
            product_name=row["product_name"],
            source_match=source_match,
            history=self.review_history(interaction_id),
        )

    def review_history(self, interaction_id: str) -> list[RuleReviewEvent]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM interaction_review_events WHERE interaction_id=? ORDER BY reviewed_at",
                (interaction_id,),
            ).fetchall()
        return [RuleReviewEvent.model_validate(dict(row)) for row in rows]

    def review_rule(self, interaction_id: str, request: RuleReviewRequest) -> RuleReviewEvent:
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT r.payload_json, r.validation_status, r.label_id, l.sections_json
                FROM interaction_rules r JOIN labels l ON l.label_id=r.label_id
                WHERE r.interaction_id=?""",
                (interaction_id,),
            ).fetchone()
            if row is None:
                raise KeyError(interaction_id)
            current = ValidationStatus(row["validation_status"])
            if current != request.expected_status:
                raise RuntimeError(
                    f"status changed: expected {request.expected_status.value}, found {current.value}"
                )
            self._validate_transition(current, request.target_status)
            rule = InteractionRule.model_validate_json(row["payload_json"])
            if request.target_status == ValidationStatus.SOURCE_SPAN_VERIFIED:
                sections = json.loads(row["sections_json"])
                blocks = sections.get(rule.source_passage.section, [])
                if not any(rule.source_passage.text in block for block in blocks):
                    raise ValueError("source passage is not an exact span of the stored label section")
            rule.validation_status = request.target_status
            connection.execute(
                "UPDATE interaction_rules SET validation_status=?, payload_json=? WHERE interaction_id=?",
                (request.target_status.value, rule.model_dump_json(), interaction_id),
            )
            event = RuleReviewEvent(
                event_id=str(uuid.uuid4()),
                interaction_id=interaction_id,
                previous_status=current,
                new_status=request.target_status,
                reviewer=request.reviewer,
                note=request.note,
                reviewed_at=datetime.now(UTC),
            )
            connection.execute(
                "INSERT INTO interaction_review_events VALUES(?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.interaction_id,
                    event.previous_status.value,
                    event.new_status.value,
                    event.reviewer,
                    event.note,
                    event.reviewed_at.isoformat(),
                ),
            )
        return event

    def add_review_note(
        self, interaction_id: str, request: ReviewNoteRequest, reviewer: str
    ) -> RuleReviewEvent:
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT validation_status FROM interaction_rules WHERE interaction_id=?",
                (interaction_id,),
            ).fetchone()
            if row is None:
                raise KeyError(interaction_id)
            current = ValidationStatus(row["validation_status"])
            if current != request.expected_status:
                raise RuntimeError(
                    f"status changed: expected {request.expected_status.value}, found {current.value}"
                )
            event = RuleReviewEvent(
                event_id=str(uuid.uuid4()),
                interaction_id=interaction_id,
                previous_status=current,
                new_status=current,
                reviewer=reviewer,
                note=f"REQUEST_{request.kind.upper()}: {request.comment}",
                reviewed_at=datetime.now(UTC),
            )
            connection.execute(
                "INSERT INTO interaction_review_events VALUES(?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.interaction_id,
                    event.previous_status.value,
                    event.new_status.value,
                    event.reviewer,
                    event.note,
                    event.reviewed_at.isoformat(),
                ),
            )
        return event

    @staticmethod
    def _validate_transition(current: ValidationStatus, target: ValidationStatus) -> None:
        allowed = {
            ValidationStatus.EXTRACTED: {
                ValidationStatus.SOURCE_SPAN_VERIFIED,
                ValidationStatus.REJECTED,
            },
            ValidationStatus.SOURCE_SPAN_VERIFIED: {
                ValidationStatus.HUMAN_REVIEWED,
                ValidationStatus.REJECTED,
            },
            ValidationStatus.HUMAN_REVIEWED: set(),
            ValidationStatus.REJECTED: set(),
        }
        if target not in allowed[current]:
            raise ValueError(f"invalid review transition: {current.value} -> {target.value}")

