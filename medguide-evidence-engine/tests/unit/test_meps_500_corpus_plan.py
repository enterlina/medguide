from scripts.build_meps_500_corpus_plan import build_plan, normalize_group, parse_rows


def test_parses_meps_markdown_row() -> None:
    rows = parse_rows("| 1 | ATORVASTATIN | 115,776,198 | 29,693,563 | 8281 |")
    assert rows[0]["source_name"] == "ATORVASTATIN"
    assert rows[0]["estimated_patients"] == 29_693_563


def test_class_is_not_automatically_ingested() -> None:
    row = normalize_group({"rank": 1, "source_name": "CARDIOVASCULAR AGENTS"})
    assert row["eligible_for_automated_ingestion"] is False
    assert row["components"] == []


def test_combination_and_form_are_preserved() -> None:
    row = normalize_group({"rank": 1, "source_name": "FLUTICASONE-SALMETEROL INHALATION"})
    assert row["components"] == ["fluticasone", "salmeterol"]
    assert row["form"] == "inhalation"


def test_build_plan_marks_existing_entity() -> None:
    plan = build_plan(
        "| 1 | METFORMIN | 10 | 9 | 8 |\n| 2 | CARDIOVASCULAR AGENTS | 7 | 6 | 5 |",
        [{"canonical_name": "metformin", "display_name": "Metformin", "aliases": []}],
    )
    assert plan["manifest"]["source_rows"] == 2
    assert plan["manifest"]["excluded_class_groups"] == 1
    assert plan["ingredient_candidates"][0]["already_in_medguide_catalog"] is True
