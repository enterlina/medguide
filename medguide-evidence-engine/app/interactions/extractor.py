from __future__ import annotations

import hashlib
import re

from app.interactions.catalog import IngredientCatalog
from app.interactions.models import (
    InteractionRule,
    InteractionStatus,
    InteractionType,
    LabelDocument,
    SourcePassage,
    TimingDirection,
    TimingRule,
)


FOOD_TARGETS = {
    "food": (InteractionType.DRUG_FOOD, ["food", "meal", "empty stomach"]),
    "dairy": (InteractionType.DRUG_FOOD, ["dairy", "milk"]),
    "grapefruit": (InteractionType.DRUG_FOOD, ["grapefruit"]),
    "fruit juice": (InteractionType.DRUG_BEVERAGE, ["fruit juice", "juice"]),
    "alcohol": (InteractionType.DRUG_BEVERAGE, ["alcohol"]),
    "coffee": (InteractionType.DRUG_BEVERAGE, ["coffee"]),
    "tea": (InteractionType.DRUG_BEVERAGE, ["tea"]),
}


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def status_from_text(text: str) -> InteractionStatus | None:
    lowered = text.casefold()
    if "contraindicated" in lowered or "must not be used" in lowered:
        return InteractionStatus.CONTRAINDICATED
    if "avoid concomitant" in lowered or "avoid combination" in lowered or "not recommended" in lowered:
        return InteractionStatus.AVOID_COMBINATION
    if re.search(r"\bmonitor(?:ing)?\b", lowered):
        return InteractionStatus.MONITORING_REQUIRED
    if any(term in lowered for term in ("separate", "hours before", "hours after", "administered at least")):
        return InteractionStatus.SEPARATE_IN_TIME
    if any(
        term in lowered
        for term in (
            "caution",
            "may increase",
            "may decrease",
            "might increase",
            "might reduce",
            "can reduce",
            "interaction",
            "interact with",
        )
    ):
        return InteractionStatus.CAUTION
    return None


def timing_from_text(text: str, subject_first: bool = True) -> TimingRule:
    lowered = text.casefold()
    match = re.search(r"(?:at least\s+)?(\d+(?:\.\d+)?)\s*hours?\s*(before|after)?", lowered)
    minutes = int(float(match.group(1)) * 60) if match else None
    qualifier = match.group(2) if match else None
    direction = TimingDirection.UNSPECIFIED
    if qualifier == "before":
        direction = TimingDirection.A_BEFORE_B if subject_first else TimingDirection.A_AFTER_B
    elif qualifier == "after":
        direction = TimingDirection.A_AFTER_B if subject_first else TimingDirection.A_BEFORE_B
    elif minutes is not None:
        direction = TimingDirection.EITHER_DIRECTION
    return TimingRule(
        minimum_interval_minutes=minutes,
        direction=direction,
        exact_interval_stated=minutes is not None,
    )


class ConservativeRuleExtractor:
    """Extract only explicit co-mentions; output remains unreviewed until validated by a human."""

    def __init__(self, catalog: IngredientCatalog):
        self.catalog = catalog

    def extract(self, label: LabelDocument, subject_id: str) -> list[InteractionRule]:
        if subject_id not in self.catalog.ingredients:
            raise ValueError("label subject must be a normalized pilot ingredient")
        rules: list[InteractionRule] = []
        for section, blocks in label.sections.items():
            for block_index, block in enumerate(blocks):
                block_sentences = sentences(block)
                for sentence in block_sentences:
                    # Very long label blocks often concatenate unrelated warnings. Co-mention
                    # extraction from them creates false pairs, so retain the source but abstain.
                    if len(sentence) > 1000:
                        continue
                    status = status_from_text(sentence)
                    if status is None:
                        continue
                    targets = self._targets(sentence, subject_id)
                    if label.source == "nih_ods":
                        # ODS fact sheets often mention food while explaining a medicine's
                        # mechanism. That is context, not automatically a food interaction.
                        targets = [
                            target
                            for target in targets
                            if target[1]
                            not in {InteractionType.DRUG_FOOD, InteractionType.DRUG_BEVERAGE}
                        ]
                        # A nutrient name can describe a biological measurement (for example,
                        # "reduce calcium absorption") without naming a second supplement.
                        # Require explicit supplement wording for supplement-to-supplement pairs.
                        targets = [
                            target
                            for target in targets
                            if self.catalog.ingredients.get(target[0]) is None
                            or self.catalog.ingredients[target[0]].ingredient_kind != "supplement"
                            or self._explicit_supplement_mention(sentence, target[0])
                        ]
                    for target_id, interaction_type in targets:
                        source_text = sentence
                        if "certain adverse effects" in sentence.casefold():
                            # Preserve the nearby official paragraphs that define an otherwise
                            # vague phrase, including the named effects and symptoms.
                            source_text = " ".join(
                                " ".join(str(value).split())
                                for value in blocks[block_index : block_index + 4]
                            )
                        effective_type = (
                            InteractionType.TIMING
                            if status == InteractionStatus.SEPARATE_IN_TIME
                            else interaction_type
                        )
                        source_id = hashlib.sha256(
                            f"{label.label_id}|{section}|{source_text}".encode()
                        ).hexdigest()[:20]
                        rules.append(
                            InteractionRule(
                                interaction_id=f"rule:{source_id}:{target_id}",
                                subject_id=subject_id,
                                object_id=target_id,
                                interaction_type=effective_type,
                                status=status,
                                effect=source_text,
                                recommended_action=source_text,
                                timing_rule=(
                                    timing_from_text(sentence)
                                    if status == InteractionStatus.SEPARATE_IN_TIME
                                    else None
                                ),
                                source_passage=SourcePassage(
                                    source_id=source_id,
                                    label_id=label.label_id,
                                    source_url=label.source_url,
                                    section=section,
                                    text=source_text,
                                ),
                            )
                        )
        return list({rule.interaction_id: rule for rule in rules}.values())

    def _explicit_supplement_mention(self, text: str, ingredient_id: str) -> bool:
        ingredient = self.catalog.ingredients[ingredient_id]
        lowered = text.casefold()
        return any(
            re.search(rf"\b{re.escape(name.casefold())}\s+supplements?\b", lowered)
            for name in [ingredient.canonical_name, *ingredient.aliases]
        )

    def _targets(self, text: str, subject_id: str) -> list[tuple[str, InteractionType]]:
        lowered = text.casefold()
        found: list[tuple[str, InteractionType]] = []
        subject = self.catalog.ingredients[subject_id]
        for ingredient in self.catalog.ingredients.values():
            if ingredient.ingredient_id == subject_id:
                continue
            names = [ingredient.canonical_name, *ingredient.aliases]
            if any(re.search(rf"\b{re.escape(name.casefold())}\b", lowered) for name in names):
                interaction_type = (
                    InteractionType.DRUG_SUPPLEMENT
                    if "supplement" in (subject.ingredient_kind, ingredient.ingredient_kind)
                    else InteractionType.DRUG_DRUG
                )
                found.append((ingredient.ingredient_id, interaction_type))
        for target, (kind, names) in FOOD_TARGETS.items():
            if any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in names):
                found.append((f"substance:{target.replace(' ', '-')}", kind))
        return found

