from scripts.discover_catalog_pubmed import select_new_entities


def test_select_new_entities_excludes_existing_names() -> None:
    entities = [
        {"entity_id": "a", "display_name": "Vitamin D"},
        {"entity_id": "b", "display_name": "Warfarin"},
    ]
    assert select_new_entities(entities, [{"name": "vitamin d"}]) == [entities[1]]
