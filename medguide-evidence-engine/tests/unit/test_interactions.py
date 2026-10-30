from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactions.adapters import DailyMedSPLAdapter, NIHODSFactSheetAdapter, OpenFDALabelAdapter
from app.interactions.catalog import IngredientCatalog
from app.interactions.engine import InteractionEngine
from app.interactions.extractor import ConservativeRuleExtractor
from app.interactions.models import (
    Ingredient,
    InteractionCheckRequest,
    LabelDocument,
    MedicationInput,
    RuleReviewRequest,
    ValidationStatus,
)
from app.interactions.repository import InteractionRepository
from app.main import app


def test_pilot_catalog_contains_bounded_ingredient_set() -> None:
    root = Path(__file__).parents[2]
    catalog = IngredientCatalog.from_json(root / "data/interactions/pilot_ingredients.json")
    assert 20 <= len(catalog.ingredients) <= 50
    resolved = catalog.resolve_local("Tylenol")
    assert resolved.canonical_names == ["acetaminophen"]
    assert resolved.resolution == "pilot_catalog_exact"


def test_openfda_parser_preserves_original_sections_and_provenance() -> None:
    label = OpenFDALabelAdapter.parse_record(
        {
            "id": "fixture-label",
            "set_id": "fixture-set",
            "effective_time": "20260101",
            "openfda": {"brand_name": ["Fixture Brand"], "rxcui": ["123"]},
            "drug_interactions": ["Explicit fixture interaction passage."],
        }
    )
    assert label.sections["drug_interactions"] == ["Explicit fixture interaction passage."]
    assert label.label_id == "openfda:fixture-label"
    assert str(label.source_url).startswith("https://api.fda.gov/")


def test_dailymed_spl_parser_extracts_only_recognized_sections() -> None:
    xml = """<document xmlns="urn:hl7-org:v3"><component><structuredBody><component>
      <section><code code="34073-7"/><text><paragraph>Drug Alpha may increase Drug Beta.</paragraph></text></section>
    </component></structuredBody></component></document>"""
    label = DailyMedSPLAdapter.parse_xml(xml, "fixture-set", "2")
    assert label.sections == {"drug_interactions": ["Drug Alpha may increase Drug Beta."]}
    assert label.set_id == "fixture-set"
    assert label.version == "2"


def test_dailymed_spl_parser_uses_official_loinc_section_codes() -> None:
    xml = """<document xmlns="urn:hl7-org:v3"><component><structuredBody>
      <component><section><code code="34068-7"/><text>Take with a meal.</text></section></component>
      <component><section><code code="34070-3"/><text>Contraindicated in condition X.</text></section></component>
      <component><section><code code="34069-5"/><text>Bottle of 30 tablets.</text></section></component>
    </structuredBody></component></document>"""
    label = DailyMedSPLAdapter.parse_xml(xml, "fixture-set", "3")
    assert label.sections == {
        "dosage_and_administration": ["Take with a meal."],
        "contraindications": ["Contraindicated in condition X."],
    }


def test_dailymed_spl_parser_classifies_numbered_generic_subsections() -> None:
    xml = """<document xmlns="urn:hl7-org:v3"><component><structuredBody>
      <component><section><code code="42229-5"/><title>5.2 Serious Infections</title>
        <text>May increase the risk of serious infections.</text></section></component>
      <component><section><code code="42229-5"/><title>8.4 Pediatric Use</title>
        <text>Safety in pediatric patients has not been established.</text></section></component>
      <component><section><code code="42229-5"/><title>17 Patient Counseling Information</title>
        <text>Tell patients to report signs of infection.</text></section></component>
    </structuredBody></component></document>"""
    label = DailyMedSPLAdapter.parse_xml(xml, "fixture-set", "4")
    assert label.sections == {
        "warnings_and_precautions": ["May increase the risk of serious infections."],
        "pediatric_use": ["Safety in pediatric patients has not been established."],
        "information_for_patients": ["Tell patients to report signs of infection."],
    }


def test_ods_parser_preserves_interaction_headings_and_source_text() -> None:
    html = """<html><body>
      <h2>Interactions with Medications</h2>
      <p>Vitamin D supplements may interact with medications.</p>
      <h3>Statins</h3>
      <p>High intakes of vitamin D might reduce the potency of atorvastatin.</p>
      <h2>References</h2><p>This must not be stored as guidance.</p>
    </body></html>"""
    label = NIHODSFactSheetAdapter.parse_html(
        html, "VitaminD", "https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/"
    )
    assert label.source == "nih_ods"
    assert label.sections == {
        "interactions_with_medications": [
            "Vitamin D supplements may interact with medications.",
            "Statins: High intakes of vitamin D might reduce the potency of atorvastatin.",
        ]
    }
    assert str(label.source_url).startswith("https://ods.od.nih.gov/")


def test_extractor_keeps_context_that_explains_vague_adverse_effects() -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(
                ingredient_id="ingredient:vitamin-d",
                canonical_name="vitamin d",
                ingredient_kind="supplement",
            ),
            Ingredient(
                ingredient_id="ingredient:calcium",
                canonical_name="calcium",
                ingredient_kind="supplement",
            ),
        ]
    )
    passage = (
        "Vitamin D toxicity can cause hypercalcemia and hypercalciuria. "
        "Vitamin D toxicity is almost always a result of excessive supplemental intake. "
        "Taking calcium supplements in combination with vitamin D supplements may increase "
        "the risk of certain adverse effects."
    )
    label = LabelDocument(
        label_id="nih-ods:vitamind",
        source="nih_ods",
        source_url="https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/",
        ingredient_ids=["ingredient:vitamin-d"],
        sections={
            "health_risks_from_excessive_vitamin_d": [
                passage,
                "The upper intake level depends on age.",
                "Excess vitamin D can cause marked hypercalcemia.",
                "Hypercalcemia can lead to nausea, weakness, thirst, and kidney stones.",
            ]
        },
        content_hash=hashlib.sha256(passage.encode()).hexdigest(),
    )
    rules = ConservativeRuleExtractor(catalog).extract(label, "ingredient:vitamin-d")
    assert len(rules) == 1
    assert "hypercalcemia" in rules[0].source_passage.text
    assert "excessive supplemental intake" in rules[0].source_passage.text
    assert "nausea, weakness, thirst, and kidney stones" in rules[0].source_passage.text


def test_ods_biological_measurement_is_not_a_supplement_pair() -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(
                ingredient_id="ingredient:vitamin-d",
                canonical_name="vitamin d",
                ingredient_kind="supplement",
            ),
            Ingredient(
                ingredient_id="ingredient:calcium",
                canonical_name="calcium",
                ingredient_kind="supplement",
            ),
        ]
    )
    text = "Corticosteroid medications can reduce calcium absorption and impair vitamin D metabolism."
    label = LabelDocument(
        label_id="nih-ods:vitamind",
        source="nih_ods",
        source_url="https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/",
        ingredient_ids=["ingredient:vitamin-d"],
        sections={"interactions_with_medications": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    assert ConservativeRuleExtractor(catalog).extract(label, "ingredient:vitamin-d") == []


def test_extraction_storage_and_pair_check_keep_exact_source_passage(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Drug beta should be administered at least 2 hours after drug alpha."
    label = LabelDocument(
        label_id="fixture:label:1",
        source="fixture",
        source_url="https://example.invalid/label/1",
        set_id="11111111-1111-1111-1111-111111111111",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    rules = ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")
    assert len(rules) == 1
    assert rules[0].status == "SEPARATE_IN_TIME"
    assert rules[0].timing_rule.minimum_interval_minutes == 120
    assert rules[0].source_passage.text == text

    repository = InteractionRepository(tmp_path / "interactions.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(label, rules)
    repository.review_rule(
        rules[0].interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
            expected_status=ValidationStatus.EXTRACTED,
            reviewer="reviewer@example.test",
            note="Exact source span confirmed in the stored fixture label.",
        ),
    )
    preliminary = InteractionEngine(catalog, repository).check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="drug beta")]
        )
    )
    assert preliminary.timing_restrictions == []
    assert len(preliminary.preliminary_findings) == 1
    assert preliminary.preliminary_findings[0].validation_status == (
        ValidationStatus.SOURCE_SPAN_VERIFIED
    )
    repository.review_rule(
        rules[0].interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus.HUMAN_REVIEWED,
            expected_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
            reviewer="reviewer@example.test",
            note="Fixture interpretation and directional timing reviewed.",
        ),
    )
    response = InteractionEngine(catalog, repository).check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="drug beta")]
        )
    )
    assert len(response.timing_restrictions) == 1
    assert response.preliminary_findings == []
    assert response.sources[0].text == text
    assert str(response.sources[0].readable_url) == (
        "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm"
        "?setid=11111111-1111-1111-1111-111111111111"
    )


def test_review_workflow_enforces_order_exact_span_and_audit_log(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Drug alpha may increase exposure to drug beta."
    label = LabelDocument(
        label_id="fixture:review:1",
        source="fixture",
        source_url="https://example.invalid/review/1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    rule = ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")[0]
    repository = InteractionRepository(tmp_path / "review.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(label, [rule])

    import pytest

    with pytest.raises(ValueError, match="invalid review transition"):
        repository.review_rule(
            rule.interaction_id,
            RuleReviewRequest(
                target_status=ValidationStatus.HUMAN_REVIEWED,
                expected_status=ValidationStatus.EXTRACTED,
                reviewer="reviewer@example.test",
                note="Attempt to skip mandatory source verification.",
            ),
        )
    first = repository.review_rule(
        rule.interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
            expected_status=ValidationStatus.EXTRACTED,
            reviewer="reviewer@example.test",
            note="Exact source span verified.",
        ),
    )
    second = repository.review_rule(
        rule.interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus.HUMAN_REVIEWED,
            expected_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
            reviewer="clinical-reviewer@example.test",
            note="Interpretation reviewed against the official fixture passage.",
        ),
    )
    assert first.previous_status == ValidationStatus.EXTRACTED
    assert second.new_status == ValidationStatus.HUMAN_REVIEWED
    assert [event.new_status for event in repository.review_history(rule.interaction_id)] == [
        ValidationStatus.SOURCE_SPAN_VERIFIED,
        ValidationStatus.HUMAN_REVIEWED,
    ]


def test_repeat_ingestion_preserves_reviewed_rule_status(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Drug alpha may increase exposure to drug beta."
    label = LabelDocument(
        label_id="fixture:repeat:1",
        source="fixture",
        source_url="https://example.invalid/repeat/1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    rule = ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")[0]
    repository = InteractionRepository(tmp_path / "repeat.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(label, [rule])
    repository.review_rule(
        rule.interaction_id,
        RuleReviewRequest(
            target_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
            expected_status=ValidationStatus.EXTRACTED,
            reviewer="reviewer@example.test",
            note="Exact source span verified before repeat ingestion.",
        ),
    )

    repository.store_label_and_rules(label, [rule])

    reviewed, total = repository.review_queue(ValidationStatus.SOURCE_SPAN_VERIFIED)
    assert total == 1
    assert reviewed[0].validation_status == ValidationStatus.SOURCE_SPAN_VERIFIED


def test_unreviewed_rules_are_not_returned_by_interaction_engine(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Drug alpha may increase exposure to drug beta."
    label = LabelDocument(
        label_id="fixture:unreviewed:1",
        source="fixture",
        source_url="https://example.invalid/unreviewed/1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    repository = InteractionRepository(tmp_path / "unreviewed.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(
        label, ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")
    )
    response = InteractionEngine(catalog, repository).check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="drug beta")]
        )
    )
    assert response.interactions == []
    assert len(response.label_mentions) == 1
    assert response.label_mentions[0].validation_status == ValidationStatus.EXTRACTED
    assert len(response.sources) == 1


def test_preliminary_rules_only_include_the_selected_combination(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
            Ingredient(ingredient_id="ingredient:gamma", canonical_name="drug gamma"),
        ]
    )
    text = "Drug beta may increase exposure to drug alpha. Drug gamma may increase exposure to drug alpha."
    label = LabelDocument(
        label_id="fixture:selection:1",
        source="fixture",
        source_url="https://example.invalid/selection/1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    repository = InteractionRepository(tmp_path / "selection.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    rules = ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")
    repository.store_label_and_rules(label, rules)
    for rule in rules:
        repository.review_rule(
            rule.interaction_id,
            RuleReviewRequest(
                target_status=ValidationStatus.SOURCE_SPAN_VERIFIED,
                expected_status=ValidationStatus.EXTRACTED,
                reviewer="reviewer@example.test",
                note="Exact source span verified for selection test.",
            ),
        )

    response = InteractionEngine(catalog, repository).check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="drug beta")]
        )
    )

    assert len(response.preliminary_findings) == 1
    assert response.preliminary_findings[0].object_id == "ingredient:beta"


def test_api_separates_official_label_guidance_from_reviewed_findings() -> None:
    response = TestClient(app).post(
        "/api/interactions/check",
        json={"medications": [{"name": "metformin"}, {"name": "lisinopril"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["interactions"] == []
    assert payload["label_guidance"]
    assert "LABEL_GUIDANCE_AVAILABLE" in {
        gap["status"] for gap in payload["coverage_gaps"]
    }
    assert "SAFE" not in response.text


def test_duplicate_active_ingredients_are_reported() -> None:
    response = TestClient(app).post(
        "/api/interactions/check",
        json={"medications": [{"name": "Tylenol"}, {"name": "acetaminophen"}]},
    )
    assert response.status_code == 200
    duplicates = response.json()["duplicate_ingredients"]
    assert duplicates[0]["canonical_name"] == "acetaminophen"


def test_single_medication_returns_its_label_guidance() -> None:
    response = TestClient(app).post(
        "/api/interactions/check",
        json={"medications": [{"name": "vitamin d"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["medications"][0]["canonical_names"] == ["vitamin d"]
    assert payload["label_guidance"]


def test_food_and_drink_rules_require_the_selected_substance(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:alpha", canonical_name="drug alpha"),
            Ingredient(ingredient_id="ingredient:beta", canonical_name="drug beta"),
        ]
    )
    text = "Grapefruit may increase exposure to drug alpha."
    label = LabelDocument(
        label_id="fixture:grapefruit:1",
        source="fixture",
        source_url="https://example.invalid/grapefruit/1",
        ingredient_ids=["ingredient:alpha"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    repository = InteractionRepository(tmp_path / "food-selection.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(
        label, ConservativeRuleExtractor(catalog).extract(label, "ingredient:alpha")
    )
    engine = InteractionEngine(catalog, repository)

    unrelated = engine.check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="drug beta")]
        )
    )
    assert unrelated.label_mentions == []

    selected = engine.check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="drug alpha"), MedicationInput(name="grapefruit")]
        )
    )
    assert len(selected.label_mentions) == 1
    assert selected.label_mentions[0].object_id == "substance:grapefruit"
    assert selected.medications[1].resolution == "supported_food_or_drink"
    assert all(gap["medication"] != "grapefruit" for gap in selected.coverage_gaps)


def test_no_effect_study_passage_is_not_shown_as_an_interaction(tmp_path: Path) -> None:
    catalog = IngredientCatalog(
        [
            Ingredient(ingredient_id="ingredient:metformin", canonical_name="metformin"),
            Ingredient(ingredient_id="ingredient:warfarin", canonical_name="warfarin"),
        ]
    )
    text = (
        "In clinical studies, sitagliptin did not meaningfully alter the pharmacokinetics "
        "of metformin or warfarin, providing evidence of a low propensity for causing "
        "drug interactions."
    )
    label = LabelDocument(
        label_id="fixture:no-effect:1",
        source="fixture",
        source_url="https://example.invalid/no-effect/1",
        ingredient_ids=["ingredient:metformin"],
        sections={"drug_interactions": [text]},
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    repository = InteractionRepository(tmp_path / "no-effect.sqlite3")
    repository.upsert_ingredients(list(catalog.ingredients.values()))
    repository.store_label_and_rules(
        label, ConservativeRuleExtractor(catalog).extract(label, "ingredient:metformin")
    )

    response = InteractionEngine(catalog, repository).check(
        InteractionCheckRequest(
            medications=[MedicationInput(name="metformin"), MedicationInput(name="warfarin")]
        )
    )

    assert response.label_mentions == []
