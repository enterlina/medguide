import publicData from "@/data/public-interactions.json";

type Resolution = {
  ingredient_ids: string[];
  canonical_names: string[];
  rxcui?: string | null;
  resolution: string;
  product_ids: string[];
  product_set_ids: string[];
};

type Rule = (typeof publicData.rules)[number];

const data = publicData as typeof publicData;
const covered = new Set(data.covered_ingredients);
const ingredientAliases = data.ingredient_aliases as Record<string, Resolution>;
const productAliases = data.product_aliases as Record<string, Resolution>;
const guidance = data.guidance as Record<string, (typeof publicData.guidance)[keyof typeof publicData.guidance]>;
const substanceAliases: Record<string, Resolution> = {
  food: substance("food"), meal: substance("food"), dairy: substance("dairy"),
  milk: substance("dairy"), grapefruit: substance("grapefruit"),
  "grapefruit juice": substance("grapefruit"), "fruit juice": substance("fruit-juice"),
  alcohol: substance("alcohol"), coffee: substance("coffee"), tea: substance("tea"),
};
const aliasesByLength = Object.entries(ingredientAliases).sort((a, b) => b[0].length - a[0].length);

function substance(name: string): Resolution {
  return {
    ingredient_ids: [`substance:${name}`], canonical_names: [name.replaceAll("-", " ")],
    resolution: "supported_food_or_drink", product_ids: [], product_set_ids: [],
  };
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function resolve(inputName: string) {
  const normalized = normalize(inputName);
  const exact = substanceAliases[normalized] ?? productAliases[normalized] ?? ingredientAliases[normalized];
  if (exact) return { input_name: inputName, ...exact };

  const found: string[] = [];
  const names: string[] = [];
  for (const [alias, resolution] of aliasesByLength) {
    if (!new RegExp(`(^|\\s)${alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|\\s)`).test(normalized)) continue;
    for (let index = 0; index < resolution.ingredient_ids.length; index += 1) {
      const ingredientId = resolution.ingredient_ids[index];
      if (!found.includes(ingredientId)) {
        found.push(ingredientId);
        names.push(resolution.canonical_names[index]);
      }
    }
  }
  return {
    input_name: inputName, ingredient_ids: found, canonical_names: names,
    resolution: found.length ? "pilot_catalog_combination" : "unresolved",
    product_ids: [], product_set_ids: [],
  };
}

function applies(rule: Rule, requested: Set<string>) {
  return requested.has(rule.subject_id) && requested.has(rule.object_id);
}

export function interactionCatalog() {
  return { ingredients: data.suggestions, products: [] as string[] };
}

export function checkInteractions(names: string[]) {
  const medications = names.map(resolve);
  const requestedIds = [...new Set(medications.flatMap((item) => item.ingredient_ids))];
  const requested = new Set(requestedIds);
  const applicable = data.rules.filter((rule) => applies(rule, requested));
  const reviewed = applicable.filter((rule) => rule.validation_status === "human_reviewed");
  const preliminary = applicable.filter((rule) => rule.validation_status === "source_span_verified");
  const labelMentions = applicable.filter((rule) => rule.validation_status === "extracted");
  const labelGuidance = medications
    .flatMap((medication) => medication.ingredient_ids.flatMap((id) => guidance[id] ?? []))
    .filter((item, index, rows) => rows.findIndex((candidate) =>
      candidate.ingredient_id === item.ingredient_id && candidate.source_url === item.source_url &&
      candidate.product_name === item.product_name) === index);
  const guidanceIds = new Set(labelGuidance.map((item) => item.ingredient_id));
  const preliminaryIds = new Set(preliminary.flatMap((rule) => [rule.subject_id, rule.object_id]));
  const reviewedIds = new Set(reviewed.flatMap((rule) => [rule.subject_id, rule.object_id]));
  const coverageGaps: Array<{ medication: string; status: string; reason: string }> = [];

  for (const medication of medications) {
    if (!medication.ingredient_ids.length) {
      coverageGaps.push({ medication: medication.input_name, status: "INSUFFICIENT_DATA", reason: "Medication could not be normalized to the public catalog." });
    }
    for (const ingredientId of medication.ingredient_ids) {
      if (ingredientId.startsWith("substance:")) continue;
      if (!covered.has(ingredientId)) coverageGaps.push({ medication: medication.input_name, status: "INSUFFICIENT_DATA", reason: "No admitted official label is available for this ingredient." });
      else if (preliminaryIds.has(ingredientId)) coverageGaps.push({ medication: medication.input_name, status: "INSUFFICIENT_DATA", reason: "Source-linked findings are shown, but clinical interpretation is still pending." });
      else if (guidanceIds.has(ingredientId)) coverageGaps.push({ medication: medication.input_name, status: "LABEL_GUIDANCE_AVAILABLE", reason: "Official label guidance is shown below." });
      else if (!reviewedIds.has(ingredientId)) coverageGaps.push({ medication: medication.input_name, status: "INSUFFICIENT_DATA", reason: "No reviewed interaction finding is available for this medication." });
    }
  }

  const owners = new Map<string, string[]>();
  for (const medication of medications) for (const ingredientId of medication.ingredient_ids) {
    owners.set(ingredientId, [...(owners.get(ingredientId) ?? []), medication.input_name]);
  }
  const duplicateIngredients = [...owners.entries()]
    .filter(([, values]) => values.length > 1)
    .map(([ingredient_id, values]) => ({ ingredient_id, canonical_name: ingredient_id.replace(/^(ingredient|substance):/, "").replaceAll("-", " "), medications: values }));
  const visible = [...reviewed, ...preliminary, ...labelMentions];
  const sources = visible.map((rule) => rule.source_passage)
    .filter((source, index, rows) => rows.findIndex((candidate) => candidate.source_id === source.source_id) === index);

  return {
    medications,
    interactions: reviewed.filter((rule) => !["timing_separation", "drug_food", "drug_beverage"].includes(rule.interaction_type)),
    timing_restrictions: reviewed.filter((rule) => rule.interaction_type === "timing_separation"),
    food_interactions: reviewed.filter((rule) => rule.interaction_type === "drug_food"),
    beverage_interactions: reviewed.filter((rule) => rule.interaction_type === "drug_beverage"),
    preliminary_findings: preliminary,
    label_mentions: labelMentions,
    label_guidance: labelGuidance,
    duplicate_ingredients: duplicateIngredients,
    coverage_gaps: coverageGaps,
    sources,
  };
}
