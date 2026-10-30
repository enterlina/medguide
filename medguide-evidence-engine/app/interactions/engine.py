from __future__ import annotations

from collections import defaultdict
import re

from pydantic import HttpUrl

from app.interactions.catalog import IngredientCatalog
from app.interactions.models import (
    InteractionCheckRequest,
    InteractionCheckResponse,
    InteractionType,
    ResolvedMedication,
    ValidationStatus,
)
from app.interactions.repository import InteractionRepository


SUBSTANCE_ALIASES: dict[str, tuple[list[str], list[str]]] = {
    "food": (["substance:food"], ["food"]),
    "meal": (["substance:food"], ["food"]),
    "dairy": (["substance:dairy"], ["dairy"]),
    "milk": (["substance:dairy"], ["dairy"]),
    "grapefruit": (["substance:grapefruit"], ["grapefruit"]),
    "grapefruit juice": (
        ["substance:grapefruit", "substance:fruit-juice"],
        ["grapefruit", "fruit juice"],
    ),
    "fruit juice": (["substance:fruit-juice"], ["fruit juice"]),
    "alcohol": (["substance:alcohol"], ["alcohol"]),
    "coffee": (["substance:coffee"], ["coffee"]),
    "tea": (["substance:tea"], ["tea"]),
}


class InteractionEngine:
    def __init__(self, catalog: IngredientCatalog, repository: InteractionRepository):
        self.catalog = catalog
        self.repository = repository

    def check(self, request: InteractionCheckRequest) -> InteractionCheckResponse:
        resolved = [self._resolve_item(item.name) for item in request.medications]
        requested_ids = list(dict.fromkeys(i for item in resolved for i in item.ingredient_ids))
        rules = self.repository.find_rules(requested_ids)
        requested = set(requested_ids)

        def applies_to_selection(rule) -> bool:
            return rule.subject_id in requested and rule.object_id in requested

        pair_rules = [
            rule
            for rule in rules
            if rule.validation_status == ValidationStatus.HUMAN_REVIEWED
            if applies_to_selection(rule)
        ]
        preliminary_rules = [
            rule
            for rule in rules
            if rule.validation_status == ValidationStatus.SOURCE_SPAN_VERIFIED
            if applies_to_selection(rule)
        ]
        actionable_pattern = re.compile(
            r"\b(?:do not take|should not take|not take|avoid|contraindicat|monitor|"
            r"may increase|may decrease|might increase|might reduce|can reduce|interact with|"
            r"increases? (?:the )?risk|serious and potentially dangerous interaction|"
            r"not recommended|separate)\b",
            re.IGNORECASE,
        )
        non_interaction_pattern = re.compile(
            r"\b(?:no clinically significant interaction|no meaningful interaction|"
            r"did not meaningfully alter|has no effect on the pharmacokinetics|"
            r"without clinically meaningful|low propensity for causing drug interactions)\b",
            re.IGNORECASE,
        )
        label_mentions = [
            rule
            for rule in rules
            if rule.validation_status == ValidationStatus.EXTRACTED
            if applies_to_selection(rule)
            if actionable_pattern.search(rule.source_passage.text)
            if not non_interaction_pattern.search(rule.source_passage.text)
        ]
        visible_rules = [*pair_rules, *preliminary_rules, *label_mentions]
        readable_urls = self.repository.readable_source_urls(
            list({rule.source_passage.label_id for rule in visible_rules})
        )
        pair_rules = [rule.model_copy(deep=True) for rule in pair_rules]
        preliminary_rules = [rule.model_copy(deep=True) for rule in preliminary_rules]
        label_mentions = [rule.model_copy(deep=True) for rule in label_mentions]
        for rule in [*pair_rules, *preliminary_rules, *label_mentions]:
            readable_url = readable_urls.get(rule.source_passage.label_id)
            rule.source_passage.readable_url = HttpUrl(readable_url) if readable_url else None
        timing = [rule for rule in pair_rules if rule.interaction_type == InteractionType.TIMING]
        food = [rule for rule in pair_rules if rule.interaction_type == InteractionType.DRUG_FOOD]
        beverages = [
            rule for rule in pair_rules if rule.interaction_type == InteractionType.DRUG_BEVERAGE
        ]
        interactions = [
            rule
            for rule in pair_rules
            if rule.interaction_type
            not in {InteractionType.TIMING, InteractionType.DRUG_FOOD, InteractionType.DRUG_BEVERAGE}
        ]
        owners: dict[str, list[str]] = defaultdict(list)
        for item in resolved:
            for ingredient_id in item.ingredient_ids:
                owners[ingredient_id].append(item.input_name)
        duplicates = [
            {
                "ingredient_id": ingredient_id,
                "canonical_name": (
                    self.catalog.ingredients[ingredient_id].canonical_name
                    if ingredient_id in self.catalog.ingredients
                    else ingredient_id.removeprefix("substance:").replace("-", " ")
                ),
                "medications": names,
            }
            for ingredient_id, names in owners.items()
            if len(names) > 1
        ]
        covered = self.repository.covered_ingredients()
        label_guidance = []
        seen_guidance: set[tuple[str, str, str | None]] = set()
        for medication in resolved:
            medication_ids = [
                item for item in medication.ingredient_ids if item in self.catalog.ingredients
            ]
            for guidance in self.repository.label_guidance(
                medication_ids, medication.product_set_ids or None
            ):
                key = (guidance.ingredient_id, str(guidance.source_url), guidance.product_name)
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    label_guidance.append(guidance)
        guidance_ingredient_ids = {item.ingredient_id for item in label_guidance}
        reviewed_ingredient_ids = {
            identifier
            for rule in pair_rules
            for identifier in (rule.subject_id, rule.object_id)
        }
        preliminary_ingredient_ids = {
            identifier
            for rule in preliminary_rules
            for identifier in (rule.subject_id, rule.object_id)
        }
        gaps = []
        for item in resolved:
            if not item.ingredient_ids:
                gaps.append(
                    {
                        "medication": item.input_name,
                        "status": "INSUFFICIENT_DATA",
                        "reason": "Medication could not be normalized to the bounded pilot catalog.",
                    }
                )
            for ingredient_id in item.ingredient_ids:
                if ingredient_id.startswith("substance:"):
                    continue
                if ingredient_id not in covered:
                    gaps.append(
                        {
                            "medication": item.input_name,
                            "status": "INSUFFICIENT_DATA",
                            "reason": "No admitted official label is available for this ingredient.",
                        }
                    )
                elif ingredient_id in preliminary_ingredient_ids:
                    gaps.append(
                        {
                            "medication": item.input_name,
                            "status": "INSUFFICIENT_DATA",
                            "reason": "Source-verified label findings are shown below, but clinical interpretation is still pending.",
                        }
                    )
                elif ingredient_id in guidance_ingredient_ids:
                    gaps.append(
                        {
                            "medication": item.input_name,
                            "status": "LABEL_GUIDANCE_AVAILABLE",
                            "reason": "Official label guidance is shown below; no source-verified interaction rule is available yet.",
                        }
                    )
                elif ingredient_id not in reviewed_ingredient_ids:
                    gaps.append(
                        {
                            "medication": item.input_name,
                            "status": "INSUFFICIENT_DATA",
                            "reason": "Official label is ingested, but no reviewed interaction finding is available for this medication.",
                        }
                    )
        sources = list(
            {
                rule.source_passage.source_id: rule.source_passage
                for rule in [*pair_rules, *preliminary_rules, *label_mentions]
            }.values()
        )
        return InteractionCheckResponse(
            medications=resolved,
            interactions=interactions,
            timing_restrictions=timing,
            food_interactions=food,
            beverage_interactions=beverages,
            preliminary_findings=preliminary_rules,
            label_mentions=label_mentions,
            label_guidance=label_guidance,
            duplicate_ingredients=duplicates,
            coverage_gaps=gaps,
            sources=sources,
        )

    def _resolve_item(self, name: str) -> ResolvedMedication:
        normalized = self.catalog.normalize(name)
        substance = SUBSTANCE_ALIASES.get(normalized)
        if substance:
            identifiers, canonical_names = substance
            return ResolvedMedication(
                input_name=name,
                ingredient_ids=identifiers,
                canonical_names=canonical_names,
                resolution="supported_food_or_drink",
            )
        return self.catalog.resolve_local(name)

