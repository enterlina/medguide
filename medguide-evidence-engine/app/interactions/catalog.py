from __future__ import annotations

import json
import re
from pathlib import Path

from app.interactions.models import Ingredient, ResolvedMedication


class IngredientCatalog:
    def __init__(self, ingredients: list[Ingredient], products: list[dict] | None = None):
        self.ingredients = {item.ingredient_id: item for item in ingredients}
        self._aliases: dict[str, str] = {}
        for item in ingredients:
            for name in [item.canonical_name, *item.aliases]:
                self._aliases[self.normalize(name)] = item.ingredient_id
        self.products = products or []
        self._product_aliases: dict[str, list[dict]] = {}
        for product in self.products:
            if not product.get("ingredient_ids"):
                continue
            for name in product.get("search_aliases", []):
                self._product_aliases.setdefault(self.normalize(name), []).append(product)

    @classmethod
    def from_json(cls, path: Path, products_path: Path | None = None) -> "IngredientCatalog":
        products = json.loads(products_path.read_text()) if products_path and products_path.exists() else []
        return cls(
            [Ingredient.model_validate(row) for row in json.loads(path.read_text())],
            products,
        )

    @staticmethod
    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    def resolve_local(self, name: str) -> ResolvedMedication:
        normalized = self.normalize(name)
        product_matches = self._product_aliases.get(normalized, [])
        if product_matches:
            ingredient_ids: list[str] = []
            product_ids: list[str] = []
            set_ids: list[str] = []
            for product in product_matches:
                product_ids.append(product["product_id"])
                set_ids.append(product["set_id"])
                for ingredient_id in product["ingredient_ids"]:
                    if ingredient_id in self.ingredients and ingredient_id not in ingredient_ids:
                        ingredient_ids.append(ingredient_id)
            return ResolvedMedication(
                input_name=name,
                ingredient_ids=ingredient_ids,
                canonical_names=[self.ingredients[item].canonical_name for item in ingredient_ids],
                resolution="pharmacy_product_exact",
                product_ids=product_ids,
                product_set_ids=set_ids,
            )
        exact = self._aliases.get(normalized)
        if exact:
            ingredient = self.ingredients[exact]
            return ResolvedMedication(
                input_name=name,
                ingredient_ids=[exact],
                canonical_names=[ingredient.canonical_name],
                rxcui=ingredient.rxcui,
                resolution="pilot_catalog_exact",
            )
        # Combination names are accepted only when every token group maps explicitly.
        found = []
        for alias, ingredient_id in sorted(self._aliases.items(), key=lambda row: -len(row[0])):
            if re.search(rf"(^|\s){re.escape(alias)}($|\s)", normalized):
                if ingredient_id not in found:
                    found.append(ingredient_id)
        return ResolvedMedication(
            input_name=name,
            ingredient_ids=found,
            canonical_names=[self.ingredients[item].canonical_name for item in found],
            resolution="pilot_catalog_combination" if found else "unresolved",
        )

