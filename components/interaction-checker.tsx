"use client";

import {
  Activity, AlertTriangle, Baby, CheckCircle2, CircleX,
  Clock3, ExternalLink, Link2, Loader2, Pin, PinOff, Search, ShieldAlert, Utensils, Wine, X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

const PINNED_ITEMS_KEY = "medguide.interactions.pinned-items";

type SourcePassage = {
  source_id: string;
  label_id: string;
  source_url: string;
  readable_url: string | null;
  section: string;
  text: string;
};

type InteractionRule = {
  interaction_id: string;
  subject_id: string;
  object_id: string;
  interaction_type: string;
  status: string;
  severity: string | null;
  effect: string;
  recommended_action: string;
  timing_rule: { minimum_interval_minutes: number | null; direction: string } | null;
  conditions: string[];
  source_passage: SourcePassage;
  validation_status: "extracted" | "source_span_verified" | "human_reviewed";
};

type CheckResponse = {
  medications: Array<{ input_name: string; ingredient_ids: string[]; canonical_names: string[]; resolution: string }>;
  interactions: InteractionRule[];
  timing_restrictions: InteractionRule[];
  food_interactions: InteractionRule[];
  beverage_interactions: InteractionRule[];
  preliminary_findings: InteractionRule[];
  label_mentions: InteractionRule[];
  label_guidance: Array<{
    ingredient_id: string;
    source_name: string;
    product_name: string | null;
    document_version: string | null;
    source_url: string;
    sections: Array<{ section: string; passage: string; excerpted: boolean }>;
  }>;
  duplicate_ingredients: Array<{ canonical_name: string; medications: string[] }>;
  coverage_gaps: Array<{ medication: string; status: string; reason: string }>;
  sources: SourcePassage[];
};

const fallbackSuggestions = [
  "Acetaminophen", "Ibuprofen", "Aspirin", "Naproxen", "Metformin",
  "Lisinopril", "Losartan", "Amlodipine", "Atorvastatin", "Simvastatin",
  "Warfarin", "Apixaban", "Levothyroxine", "Omeprazole", "Sertraline",
  "Fluoxetine", "Gabapentin", "Amoxicillin", "Azithromycin", "Ciprofloxacin",
  "Doxycycline", "Calcium", "Iron supplement", "Magnesium", "Vitamin D",
  "Vitamin K", "Prednisone",
  "Grapefruit", "Grapefruit juice", "Alcohol", "Coffee", "Tea", "Milk", "Food",
];

type FindingFilter = "all" | "together" | "timing" | "food" | "drink";

const findingFilters: Array<{ key: FindingFilter; label: string; icon: typeof Activity }> = [
  { key: "all", label: "All findings", icon: Activity },
  { key: "together", label: "Take together", icon: Link2 },
  { key: "timing", label: "Separate by time", icon: Clock3 },
  { key: "food", label: "With food", icon: Utensils },
  { key: "drink", label: "With drinks", icon: Wine },
];

function displayName(identifier: string) {
  return identifier.replace(/^(ingredient|substance):/, "").replaceAll("-", " ");
}

function findingTitle(rule: InteractionRule) {
  const subject = displayName(rule.subject_id);
  const object = displayName(rule.object_id);
  if (rule.interaction_type === "timing_separation") return `${subject} and ${object} may need separation`;
  if (rule.interaction_type === "drug_food") return `${subject}: food instructions found`;
  if (rule.interaction_type === "drug_beverage") return `${subject} and ${object}`;
  return `${subject} and ${object}`;
}

function ruleText(rule: InteractionRule) {
  return `${rule.effect} ${rule.recommended_action} ${rule.source_passage.text}`.toLowerCase();
}

function namedFoodOrBotanicalExamples(rule: InteractionRule) {
  const match = rule.source_passage.text.match(/\be\.g\.,?\s*([^)]+)/i);
  if (!match) return [];
  return match[1]
    .split(/,|\band\b/i)
    .map((item) => item.trim().replace(/[.;:]$/, ""))
    .filter(Boolean)
    .slice(0, 6);
}

function readableList(items: string[]) {
  if (items.length < 2) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

function normalizedIdentifier(identifier: string) {
  return displayName(identifier).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function passageNamesBothSides(rule: InteractionRule) {
  const text = rule.source_passage.text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ");
  return text.includes(normalizedIdentifier(rule.subject_id)) && text.includes(normalizedIdentifier(rule.object_id));
}

function specificEffect(rule: InteractionRule) {
  const effect = rule.effect.trim();
  if (effect.length < 12) return null;
  if (/^(possible|potential|unknown|unspecified)?\s*(drug[- ]?)?interaction\.?$/i.test(effect)) return null;
  if (/official label describes|check (the|this) combination/i.test(effect)) return null;
  return effect;
}

function findingSummary(rule: InteractionRule) {
  const text = ruleText(rule);
  if (rule.interaction_type === "timing_separation") {
    const minutes = rule.timing_rule?.minimum_interval_minutes;
    return minutes
      ? `The official label specifies at least ${minutes / 60} hours between them.`
      : "The official label recommends taking these at different times.";
  }
  if (text.includes("aspirin") && (rule.subject_id.includes("warfarin") || rule.object_id.includes("warfarin"))) return "Taking warfarin and aspirin together can increase the risk of bleeding.";
  if (text.includes("vitamin k") && text.includes("warfarin") && (text.includes("anticoagulant") || text.includes("clotting"))) return "Sudden changes in vitamin K intake can make warfarin’s blood-thinning effect stronger or weaker. This can change the risk of bleeding or blood clots.";
  if (text.includes("calcium supplements") && text.includes("vitamin d supplements")) return "High supplemental doses can raise calcium in the blood or urine. Possible effects include nausea, vomiting, weakness, strong thirst, frequent urination, and kidney stones.";
  if (text.includes("hypercalcemia")) return "This combination can raise calcium in the blood. Possible signs include nausea, weakness, strong thirst, frequent urination, or kidney stones.";
  if (text.includes("metformin") && text.includes("alcohol") && (text.includes("lactic acidosis") || text.includes("lactate metabolism"))) return "Heavy or frequent alcohol use can make lactic acid build up while taking metformin. This can cause a rare but serious condition called lactic acidosis.";
  if (text.includes("metformin") && text.includes("carbonic anhydrase inhibitor")) return "Medicines such as topiramate or acetazolamide can change the body’s acid balance. With metformin, this can raise the risk of lactic acidosis.";
  if (text.includes("bleed")) return "Taking these together may increase the risk of bleeding.";
  if (text.includes("coagulation") || text.includes("prothrombin") || text.includes("inr")) return "Taking these together may change blood clotting and may require a blood test (INR).";
  if (text.includes("no clinically significant") || text.includes("did not meaningfully alter") || text.includes("has no effect")) return "The official label reports that no meaningful interaction was found in the cited study.";
  if (rule.interaction_type === "drug_food") {
    const examples = namedFoodOrBotanicalExamples(rule);
    if (examples.length) return `The label specifically names ${readableList(examples)}. These foods or botanicals may change how the body processes this medicine.`;
    if (text.includes("grapefruit")) return "Grapefruit or grapefruit juice may change the amount of this medicine in the blood.";
    if (text.includes("dairy") || text.includes("milk")) return "Milk or other dairy products may reduce how much of this medicine the body absorbs.";
    return "The source identifies a food-related interaction, but does not name a more specific food in this passage.";
  }
  if (rule.interaction_type === "drug_beverage" && text.includes("alcohol")) return "Alcohol can increase this medicine’s side effects. The exact risk depends on the medicine and how much alcohol is used.";
  return specificEffect(rule);
}

function actionSummary(rule: InteractionRule) {
  const text = ruleText(rule);
  if (rule.interaction_type === "timing_separation") {
    const minutes = rule.timing_rule?.minimum_interval_minutes;
    return minutes ? `Leave at least ${minutes / 60} hours between doses.` : "Take them at different times as directed on the label.";
  }
  if (text.includes("aspirin") && (rule.subject_id.includes("warfarin") || rule.object_id.includes("warfarin"))) return "Do not start or stop aspirin while taking warfarin. Ask your prescriber before using them together.";
  if (text.includes("vitamin k") && text.includes("warfarin") && (text.includes("anticoagulant") || text.includes("clotting"))) return "Keep your vitamin K intake consistent from week to week. Before changing supplements or diet substantially, ask the clinician who monitors your warfarin.";
  if (text.includes("calcium supplements") && text.includes("vitamin d supplements")) return "This warning mainly concerns high total doses. Check every product label so calcium or vitamin D is not counted twice, and do not exceed the recommended amount.";
  if (text.includes("hypercalcemia")) return "Check your total vitamin D and calcium intake. Ask a clinician before using high doses, especially with kidney or parathyroid problems.";
  if (text.includes("metformin") && text.includes("alcohol") && (text.includes("lactic acidosis") || text.includes("lactate metabolism"))) return "Avoid heavy drinking. Ask your prescriber what amount of alcohol is safe for you while taking metformin.";
  if (text.includes("metformin") && text.includes("carbonic anhydrase inhibitor")) return "Ask a doctor or pharmacist before combining these medicines. You may need closer monitoring.";
  if (text.includes("monitor") || text.includes("inr") || text.includes("prothrombin")) return "Ask your prescriber whether you need closer INR monitoring.";
  if (text.includes("bleed")) return "Check with a doctor or pharmacist before combining them, especially if you bruise or bleed easily.";
  if (text.includes("avoid") || text.includes("not recommended")) return "Avoid the combination unless your prescriber has specifically approved it.";
  if (rule.interaction_type === "drug_food") {
    const examples = namedFoodOrBotanicalExamples(rule);
    if (examples.length) return `Check ${readableList(examples)} before using them with this medicine. Open the source for the exact instruction.`;
    if (text.includes("grapefruit")) return "Check the label before eating grapefruit or drinking grapefruit juice while taking this medicine.";
    if (text.includes("dairy") || text.includes("milk")) return "Follow the label’s timing instructions for milk and dairy products.";
  }
  if (text.includes("no clinically significant") || text.includes("did not meaningfully alter") || text.includes("has no effect")) return "No special action is stated in this passage; continue to follow your prescribed plan.";
  const action = rule.recommended_action.trim();
  if (action && action.toLowerCase() !== rule.effect.trim().toLowerCase() && !/possible interaction|check (the|this) combination/i.test(action)) return action;
  return "Read the source details or ask a pharmacist how this warning applies to you.";
}

function ruleKey(rule: InteractionRule) {
  const pair = [rule.subject_id, rule.object_id].sort().join("|");
  return `${pair}|${rule.interaction_type}`;
}

function isNonInteractionFinding(rule: InteractionRule) {
  const text = `${rule.effect} ${rule.recommended_action} ${rule.source_passage.text}`.toLowerCase();
  return [
    "no clinically significant interaction",
    "no meaningful interaction",
    "did not meaningfully alter",
    "has no effect on the pharmacokinetics",
    "without clinically meaningful",
    "low propensity for causing drug interactions",
  ].some((phrase) => text.includes(phrase));
}

function dedupeRules(rules: InteractionRule[]) {
  const byPair = new Map<string, InteractionRule>();
  for (const rule of rules) {
    const key = ruleKey(rule);
    const current = byPair.get(key);
    if (!current || rule.source_passage.text.length > current.source_passage.text.length) byPair.set(key, rule);
  }
  return [...byPair.values()];
}

function riskFocus(rule: InteractionRule) {
  const text = `${rule.effect} ${rule.recommended_action}`.toLowerCase();
  const severity = rule.severity?.toLowerCase();
  if (["critical", "contraindicated", "major", "high", "severe"].includes(severity ?? "")) return { label: "High risk", tone: "bg-rose-50 text-rose-700" };
  if (["moderate", "medium"].includes(severity ?? "")) return { label: "Moderate risk", tone: "bg-orange-50 text-orange-700" };
  if (["minor", "low"].includes(severity ?? "")) return { label: "Low risk", tone: "bg-blue-50 text-blue-700" };
  if (text.includes("calcium supplements") && text.includes("vitamin d supplements")) return { label: "High-dose risk", tone: "bg-orange-50 text-orange-700" };
  if (text.includes("vitamin k") && text.includes("warfarin")) return { label: "Clotting control", tone: "bg-amber-50 text-amber-700" };
  if (text.includes("hypercalcemia")) return { label: "High blood calcium", tone: "bg-orange-50 text-orange-700" };
  if (text.includes("bleed")) return { label: "Bleeding risk", tone: "bg-amber-50 text-amber-700" };
  if (text.includes("aspirin") && text.includes("not take")) return { label: "Do not combine without advice", tone: "bg-amber-50 text-amber-700" };
  if (text.includes("inr") || text.includes("coagulation") || text.includes("prothrombin")) return { label: "Blood clotting", tone: "bg-amber-50 text-amber-700" };
  if (rule.status === "CONTRAINDICATED" || rule.status === "AVOID_COMBINATION") return { label: "Avoid combination", tone: "bg-rose-50 text-rose-700" };
  if (rule.interaction_type === "timing_separation") return { label: "Separate doses", tone: "bg-violet-50 text-violet-700" };
  if (rule.interaction_type === "drug_food") return { label: "Food interaction", tone: "bg-emerald-50 text-emerald-700" };
  if (rule.interaction_type === "drug_beverage") return { label: "Drink interaction", tone: "bg-sky-50 text-sky-700" };
  return { label: "Interaction", tone: "bg-amber-50 text-amber-700" };
}

function FindingCard({ rule }: { rule: InteractionRule }) {
  const sourceUrl = rule.source_passage.readable_url ?? rule.source_passage.source_url;
  const critical = rule.status === "CONTRAINDICATED" || rule.status === "AVOID_COMBINATION";
  const focus = riskFocus(rule);
  const sourceLabel = rule.source_passage.label_id.startsWith("dailymed:")
    ? "DailyMed"
    : rule.source_passage.label_id.startsWith("nih-ods:")
      ? "NIH ODS"
      : "FDA label";
  return (
    <article className={`rounded-[14px] border-l-4 bg-white px-4 py-4 shadow-sm ${critical ? "border-l-rose-500" : "border-l-amber-400"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2"><strong className="capitalize text-[14px] text-text-primary">{findingTitle(rule)}</strong><span className={`rounded-pill px-2.5 py-1 text-[10px] font-extrabold ${focus.tone}`}>{focus.label}</span></div>
        <a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-700 hover:underline">{sourceLabel}<ExternalLink size={10} /></a>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div><p className="text-[9px] font-extrabold uppercase tracking-[0.07em] text-text-tertiary">What this means</p><p className="mt-1 text-[12px] leading-5 text-text-secondary">{findingSummary(rule)}</p></div>
        <div><p className="text-[9px] font-extrabold uppercase tracking-[0.07em] text-text-tertiary">What to do</p><p className="mt-1 text-[12px] leading-5 text-text-secondary">{actionSummary(rule)}</p></div>
      </div>
      <details className="mt-2"><summary className="w-fit cursor-pointer text-[10px] font-bold text-text-tertiary hover:text-text-primary">Details</summary>{rule.conditions.length > 0 && <p className="mt-2 text-[11px] text-text-secondary"><strong>Applies when:</strong> {rule.conditions.join(" · ")}</p>}<blockquote className="mt-2 border-l-2 border-slate-200 pl-3 text-[11px] leading-5 text-text-tertiary">{rule.source_passage.text}</blockquote></details>
    </article>
  );
}

type GuidanceItem = {
  label: string;
  text: string;
  tone: string;
  action: string;
  icon: typeof Clock3;
  sourceUrl: string;
  sourceName: string;
  fullText?: string;
  excerpted?: boolean;
};

const sectionPresentation: Record<string, Pick<GuidanceItem, "label" | "tone" | "action" | "icon">> = {
  dosage_and_administration: { label: "How to take", tone: "bg-emerald-50 text-emerald-700", action: "Follow directions", icon: Clock3 },
  instructions_for_use: { label: "How to use", tone: "bg-emerald-50 text-emerald-700", action: "Follow directions", icon: Clock3 },
  information_for_patients: { label: "Important", tone: "bg-blue-50 text-blue-700", action: "Read guidance", icon: Activity },
  indications_and_usage: { label: "Used for", tone: "bg-blue-50 text-blue-700", action: "See uses", icon: Activity },
  drug_interactions: { label: "Interactions", tone: "bg-amber-50 text-amber-700", action: "Check combinations", icon: AlertTriangle },
  contraindications: { label: "Do not use", tone: "bg-rose-50 text-rose-700", action: "Check restrictions", icon: CircleX },
  adverse_reactions: { label: "Side effects", tone: "bg-orange-50 text-orange-700", action: "Read warning", icon: AlertTriangle },
  pregnancy: { label: "Pregnancy", tone: "bg-pink-50 text-pink-700", action: "Read guidance", icon: Baby },
  lactation: { label: "Breastfeeding", tone: "bg-pink-50 text-pink-700", action: "Read guidance", icon: Baby },
  pediatric_use: { label: "Children", tone: "bg-blue-50 text-blue-700", action: "Check age", icon: ShieldAlert },
  geriatric_use: { label: "Older adults", tone: "bg-blue-50 text-blue-700", action: "Read guidance", icon: ShieldAlert },
  use_in_specific_populations: { label: "Who should check", tone: "bg-blue-50 text-blue-700", action: "Read guidance", icon: ShieldAlert },
  warnings_and_precautions: { label: "Warning", tone: "bg-orange-50 text-orange-700", action: "Use caution", icon: ShieldAlert },
  warnings_and_cautions: { label: "Warning", tone: "bg-orange-50 text-orange-700", action: "Use caution", icon: ShieldAlert },
  warnings: { label: "Warning", tone: "bg-orange-50 text-orange-700", action: "Use caution", icon: ShieldAlert },
  precautions: { label: "Precaution", tone: "bg-orange-50 text-orange-700", action: "Use caution", icon: ShieldAlert },
  ask_doctor_or_pharmacist: { label: "Ask first", tone: "bg-blue-50 text-blue-700", action: "Ask pharmacist", icon: AlertTriangle },
  do_not_use: { label: "Do not use", tone: "bg-rose-50 text-rose-700", action: "Check restrictions", icon: CircleX },
  interactions_with_medications: { label: "Interactions", tone: "bg-amber-50 text-amber-700", action: "Check combinations", icon: AlertTriangle },
  recommended_intakes: { label: "Daily intake", tone: "bg-emerald-50 text-emerald-700", action: "Check amount", icon: Activity },
};

function readableLabelSentence(section: string, passage: string) {
  const cleaned = passage
    .replace(/^\s*\d+(?:\.\d+)?\s*/i, "")
    .replace(/^(dosage and administration|drug interactions|contraindications|warnings and precautions|warnings and cautions|warnings|precautions|patient counseling information)\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();
  const candidates = cleaned.split(/(?<=[.!?])\s+/).map((sentence) => sentence.trim());
  const keywords: Record<string, RegExp> = {
    dosage_and_administration: /\b(take|administer|dose|dosing|with food|empty stomach|once daily|twice daily)\b/i,
    instructions_for_use: /\b(take|use|administer|do not|before|after)\b/i,
    information_for_patients: /\b(advise|tell|avoid|do not|risk|contact|monitor)\b/i,
    indications_and_usage: /\b(indicated|treatment|treat|used for)\b/i,
    drug_interactions: /\b(concomitant|interaction|increase|decrease|reduce|avoid|inhibitor|inducer)\b/i,
    contraindications: /\b(contraindicated|do not use|hypersensitivity|allergic)\b/i,
    adverse_reactions: /\b(adverse|common|serious|infection|reaction|risk)\b/i,
    pregnancy: /\b(pregnan|fetal|birth|risk)\b/i,
    lactation: /\b(lactation|breastfeed|milk|infant)\b/i,
    pediatric_use: /\b(pediatric|children|years of age|safety)\b/i,
    geriatric_use: /\b(geriatric|older|65 years|elderly)\b/i,
    use_in_specific_populations: /\b(pregnan|lactation|pediatric|geriatric|renal|hepatic)\b/i,
    warnings_and_precautions: /\b(may cause|risk|warning|monitor|avoid|serious|fatal)\b/i,
    warnings_and_cautions: /\b(may cause|risk|warning|monitor|avoid|serious|fatal)\b/i,
    warnings: /\b(may cause|risk|warning|monitor|avoid|serious|fatal)\b/i,
    precautions: /\b(may cause|risk|monitor|avoid|caution)\b/i,
    ask_doctor_or_pharmacist: /\b(ask|doctor|pharmacist|taking)\b/i,
    do_not_use: /\b(do not use|allergic|taking)\b/i,
    interactions_with_medications: /\b(interact|anticoagulant|bleeding|medication|chemotherapy|radiotherapy)\b/i,
    recommended_intakes: /\b(recommended|allowance|intake|adults|daily)\b/i,
  };
  const matcher = keywords[section];
  const selected = candidates.find((sentence) => sentence.length >= 35 && sentence.length <= 360 && (!matcher || matcher.test(sentence)))
    ?? candidates.find((sentence) => sentence.length >= 35 && sentence.length <= 360);
  if (!selected) return null;
  return selected.length > 240 ? `${selected.slice(0, 237).trimEnd()}…` : selected;
}

function plainGuidance(labelGuidance: CheckResponse["label_guidance"]) {
  const items: GuidanceItem[] = [];
  const fallbacks: GuidanceItem[] = [];
  const add = (item: GuidanceItem) => {
    if (!items.some((current) => current.label === item.label && current.text === item.text)) items.push(item);
  };
  for (const source of labelGuidance) {
    for (const section of source.sections) {
      const text = section.passage.toLowerCase();
      const common = {
        sourceUrl: source.source_url,
        sourceName: source.source_name === "openfda" ? "FDA label" : source.source_name === "nih_ods" ? "NIH ODS" : "DailyMed",
        fullText: section.passage,
        excerpted: section.excerpted,
      };
      const presentation = sectionPresentation[section.section];
      const fallbackText = presentation ? readableLabelSentence(section.section, section.passage) : null;
      if (presentation && fallbackText && !fallbacks.some((item) => item.label === presentation.label && item.text === fallbackText)) {
        fallbacks.push({ ...presentation, text: fallbackText, ...common });
      }
      if (text.includes("severe liver damage")) add({ label: "Liver", text: "Too much acetaminophen, or combining several acetaminophen products, can cause severe liver damage.", tone: "bg-orange-50 text-orange-700", action: "Dose limit", icon: ShieldAlert, ...common });
      if (text.includes("allergic") || text.includes("hypersensitivity")) add({ label: "Allergy", text: "Do not use if you have had an allergic reaction to this medicine or its ingredients.", tone: "bg-rose-50 text-rose-700", action: "Do not use", icon: CircleX, ...common });
      if (section.section === "dosage_and_administration" && text.includes("inr")) add({ label: "Monitoring", text: "Take only the prescribed dose and keep scheduled INR blood tests.", tone: "bg-blue-50 text-blue-700", action: "INR tests", icon: Activity, ...common });
      if (text.includes("do not take a double dose") || text.includes("do not double")) add({ label: "Missed dose", text: "Do not double the next dose after a missed dose.", tone: "bg-violet-50 text-violet-700", action: "Do not double", icon: Clock3, ...common });
      if (text.includes("with food") || text.includes("with a meal")) add({ label: "Food", text: "Take this medicine with food or a meal, as stated on the label.", tone: "bg-emerald-50 text-emerald-700", action: "With food", icon: Utensils, ...common });
      if (text.includes("gastric irritation") && text.includes("food or milk")) add({ label: "Food", text: "Taking prednisone with food or milk may reduce stomach irritation.", tone: "bg-emerald-50 text-emerald-700", action: "With food", icon: Utensils, ...common });
      if (text.includes("administered in the morning prior to 9 am")) add({ label: "Morning", text: "For a once-daily dose, the label recommends taking prednisone in the morning before 9 AM.", tone: "bg-sky-50 text-sky-700", action: "Before 9 AM", icon: Clock3, ...common });
      if (text.includes("empty stomach")) add({ label: "Food", text: "Take this medicine on an empty stomach, as stated on the label.", tone: "bg-emerald-50 text-emerald-700", action: "Empty stomach", icon: Utensils, ...common });
      if (text.includes("gradual reduction of dosage") || text.includes("gradually reduced")) add({ label: "Stopping", text: "Prednisone may need to be reduced gradually. Do not stop it suddenly unless your prescriber tells you how.", tone: "bg-orange-50 text-orange-700", action: "Taper dose", icon: AlertTriangle, ...common });
      if (text.includes("may mask some signs of infection") || text.includes("decreased resistance") && text.includes("infection")) add({ label: "Infection", text: "Prednisone can hide some signs of infection and reduce the body’s ability to fight infection.", tone: "bg-orange-50 text-orange-700", action: "Watch symptoms", icon: ShieldAlert, ...common });
      if (text.includes("systemic fungal infections") && text.includes("contraindicat")) add({ label: "Fungal infection", text: "Do not use prednisone for a systemic fungal infection unless the prescribing clinician has specifically directed it.", tone: "bg-rose-50 text-rose-700", action: "Do not use", icon: CircleX, ...common });
      if (section.section === "drug_interactions" && text.includes("bleed")) add({ label: "Bleeding", text: "Some medicines, antibiotics, supplements, or herbs can increase bleeding risk.", tone: "bg-amber-50 text-amber-700", action: "Check combinations", icon: AlertTriangle, ...common });
      if (section.section === "interactions_with_medications" && text.includes("vitamin e") && text.includes("risk of bleeding")) add({ label: "Blood thinners", text: "High-dose vitamin E can increase bleeding risk with warfarin and other blood-thinning or antiplatelet medicines.", tone: "bg-amber-50 text-amber-700", action: "Check dose", icon: AlertTriangle, ...common });
      if (section.section === "interactions_with_medications" && text.includes("vitamin e") && text.includes("simvastatin") && text.includes("niacin")) add({ label: "Simvastatin + niacin", text: "A combination of antioxidant supplements that included vitamin E reduced the expected rise in protective HDL cholesterol in people taking simvastatin with niacin.", tone: "bg-amber-50 text-amber-700", action: "Ask prescriber", icon: Activity, ...common });
      if (section.section === "interactions_with_medications" && text.includes("vitamin e") && text.includes("chemotherapy") && text.includes("radiotherapy")) add({ label: "Cancer treatment", text: "Antioxidant supplements may reduce the intended effect of some chemotherapy or radiotherapy. Evidence is uncertain, so the oncology team should review their use.", tone: "bg-orange-50 text-orange-700", action: "Ask oncology team", icon: ShieldAlert, ...common });
      if (text.includes("warfarin") && (section.section === "ask_doctor_or_pharmacist" || section.section === "drug_interactions")) add({ label: "Interaction", text: "Check with a doctor or pharmacist before combining this medicine with warfarin.", tone: "bg-amber-50 text-amber-700", action: "Ask first", icon: AlertTriangle, ...common });
      if (text.includes("sudden changes in vitamin k intakes") && text.includes("anticoagulant effect")) add({ label: "Warfarin", text: "Keep vitamin K intake consistent. Sudden changes can make warfarin’s effect stronger or weaker, changing bleeding or clot risk.", tone: "bg-amber-50 text-amber-700", action: "Keep intake steady", icon: Activity, ...common });
      if (text.includes("antibiotics can destroy vitamin k-producing bacteria")) add({ label: "Antibiotics", text: "Long courses of some antibiotics can lower vitamin K levels by reducing vitamin K-producing gut bacteria.", tone: "bg-blue-50 text-blue-700", action: "Check long courses", icon: AlertTriangle, ...common });
      if (text.includes("bile acid sequestrants") && text.includes("reduce the absorption of vitamin k")) add({ label: "Absorption", text: "Cholestyramine and colestipol can reduce vitamin K absorption, especially with long-term use.", tone: "bg-violet-50 text-violet-700", action: "Monitor levels", icon: Activity, ...common });
      if (text.includes("orlistat") && text.includes("reduce the absorption") && text.includes("vitamin k")) add({ label: "Orlistat", text: "Orlistat can reduce vitamin K absorption. The source recommends discussing an appropriate multivitamin and timing plan.", tone: "bg-emerald-50 text-emerald-700", action: "Check timing", icon: Clock3, ...common });
      if (text.includes("mvms providing nutrients") && text.includes("warfarin") && text.includes("vitamin k")) add({ label: "Warfarin", text: "A multivitamin containing vitamin K can weaken warfarin’s effect. Keep vitamin K intake consistent and check the product label.", tone: "bg-amber-50 text-amber-700", action: "Check vitamin K", icon: Activity, ...common });
      if (text.includes("not known to have any clinically relevant interactions with medications")) add({ label: "Interactions", text: "NIH ODS reports no known clinically relevant medication interactions for riboflavin (vitamin B2).", tone: "bg-emerald-50 text-emerald-700", action: "No known interaction", icon: CheckCircle2, ...common });
      if (text.includes("taken orally with or without food")) add({ label: "Food", text: "This medicine can be taken with or without food.", tone: "bg-emerald-50 text-emerald-700", action: "Either is acceptable", icon: Utensils, ...common });
      if (text.includes("respiratory depression and sedation") && text.includes("opioid")) add({ label: "Opioids", text: "Combining this medicine with opioids can cause severe sleepiness or dangerously slow breathing.", tone: "bg-rose-50 text-rose-700", action: "Ask before combining", icon: ShieldAlert, ...common });
      if (text.includes("angioedema") && text.includes("report immediately")) add({ label: "Swelling", text: "Get urgent help for swelling of the face, lips, tongue, or throat, or trouble breathing.", tone: "bg-rose-50 text-rose-700", action: "Urgent help", icon: ShieldAlert, ...common });
      if (text.includes("within 36 hours") && text.includes("sacubitril")) add({ label: "Sacubitril", text: "Do not take this medicine within 36 hours of sacubitril/valsartan because of angioedema risk.", tone: "bg-rose-50 text-rose-700", action: "Separate 36 hours", icon: Clock3, ...common });
      if (text.includes("grapefruit")) add({ label: "Grapefruit", text: "Check the official label before using grapefruit or grapefruit juice with this medicine.", tone: "bg-lime-50 text-lime-700", action: "Check food", icon: Utensils, ...common });
      if (text.includes("metformin") && text.includes("alcohol") && (text.includes("lactic acidosis") || text.includes("lactate metabolism"))) add({ label: "Alcohol", text: "Heavy or frequent drinking can make lactic acid build up while taking metformin. This is rare, but it can become a medical emergency.", tone: "bg-orange-50 text-orange-700", action: "Avoid heavy drinking", icon: Wine, ...common });
      else if (text.includes("alcohol") && (text.includes("drows") || text.includes("sleep") || text.includes("sedat"))) add({ label: "Alcohol", text: "Alcohol can make sleepiness, dizziness, or slowed reactions worse while taking this medicine.", tone: "bg-sky-50 text-sky-700", action: "Avoid or limit", icon: Wine, ...common });
      else if (text.includes("alcohol") && text.includes("liver")) add({ label: "Alcohol", text: "Alcohol and this medicine can both affect the liver. Using them together can increase the chance of liver damage.", tone: "bg-orange-50 text-orange-700", action: "Check before drinking", icon: Wine, ...common });
      else if (text.includes("alcohol")) add({ label: "Alcohol", text: "The label warns that alcohol can increase this medicine’s side effects. Open the source below for the exact warning.", tone: "bg-sky-50 text-sky-700", action: "Use caution", icon: Wine, ...common });
      if (text.includes("metformin") && text.includes("carbonic anhydrase inhibitor")) add({ label: "Acid balance", text: "Medicines such as topiramate or acetazolamide can change the body’s acid balance. With metformin, this can raise the risk of lactic acidosis.", tone: "bg-amber-50 text-amber-700", action: "Check combination", icon: AlertTriangle, ...common });
      if (text.includes("metformin") && text.includes("egfr") && (text.includes("below 30") || text.includes("less than 30"))) add({ label: "Kidneys", text: "Do not use metformin if your kidneys are severely impaired. Poor kidney function can allow metformin to build up and raise the risk of lactic acidosis.", tone: "bg-rose-50 text-rose-700", action: "Do not use", icon: CircleX, ...common });
      if (text.includes("contraindicated") && text.includes("pregnan")) add({ label: "Pregnancy", text: "This medicine may be unsafe during pregnancy; contact the prescribing clinician promptly.", tone: "bg-pink-50 text-pink-700", action: "Ask clinician", icon: Baby, ...common });
      if (text.includes("orlistat") && text.includes("absorption of vitamin d")) add({ label: "Orlistat", text: "Orlistat can reduce how much vitamin D your body absorbs.", tone: "bg-amber-50 text-amber-700", action: "Check vitamin D", icon: AlertTriangle, ...common });
      if (text.includes("vitamin d") && text.includes("potency") && text.includes("statin")) add({ label: "Statins", text: "High vitamin D intake may change how some statins work, including atorvastatin and simvastatin.", tone: "bg-amber-50 text-amber-700", action: "Ask pharmacist", icon: AlertTriangle, ...common });
      if (text.includes("corticosteroid") && text.includes("vitamin d metabolism")) add({ label: "Steroids", text: "Corticosteroids such as prednisone can interfere with vitamin D and calcium balance.", tone: "bg-amber-50 text-amber-700", action: "Check levels", icon: Activity, ...common });
      if (text.includes("thiazide") && text.includes("hypercalcemia")) add({ label: "Thiazides", text: "Vitamin D with a thiazide water pill may raise blood calcium, especially with kidney or parathyroid problems.", tone: "bg-orange-50 text-orange-700", action: "Ask clinician", icon: ShieldAlert, ...common });
    }
  }
  for (const fallback of fallbacks) add(fallback);
  return items.slice(0, 5);
}

function GuidanceRow({ item }: { item: GuidanceItem }) {
  const Icon = item.icon;
  const canExpand = Boolean(item.fullText && item.fullText.trim() !== item.text.trim());
  return <li className="grid gap-2 py-3 sm:grid-cols-[145px_minmax(0,1fr)_auto] sm:items-start">
    <span className={`inline-flex w-fit items-center gap-1.5 rounded-pill px-2.5 py-1.5 text-[10px] font-extrabold ${item.tone}`}><Icon size={13} />{item.label}</span>
    <div><p className="text-[12px] leading-5 text-text-secondary">{item.text}</p>{canExpand && <details className="mt-1"><summary className="w-fit cursor-pointer text-[10px] font-bold text-blue-700 hover:underline">Read more</summary><p className="mt-2 whitespace-pre-line text-[11px] leading-5 text-text-tertiary">{item.fullText}{item.excerpted ? "…" : ""}</p></details>}</div>
    <span className="flex items-center gap-2 sm:justify-end"><span className="rounded-pill bg-white px-2.5 py-1 text-[10px] font-bold text-slate-600">{item.action}</span><a href={item.sourceUrl} target="_blank" rel="noreferrer" aria-label={`Open ${item.sourceName}`} className="text-blue-700 hover:text-blue-900"><ExternalLink size={12} /></a></span>
  </li>;
}

function MedicationSummaryCard({
  medication,
  labelGuidance,
}: {
  medication: CheckResponse["medications"][number];
  labelGuidance: CheckResponse["label_guidance"];
}) {
  const guidance = plainGuidance(labelGuidance);
  const name = medication.canonical_names.join(" + ") || medication.input_name;
  return <article className="rounded-[14px] bg-slate-50/70 px-4 py-4">
    <h3 className="text-[15px] font-extrabold capitalize text-brand-navy">{name}</h3>
    {guidance.length > 0 ? <ul className="mt-2 divide-y divide-border">{guidance.map((item) => <GuidanceRow key={`${item.label}-${item.text}`} item={item} />)}</ul> : <div className="mt-2 flex flex-wrap items-center justify-between gap-2"><p className="text-[12px] text-text-tertiary">No practical instruction has been extracted from the available source yet.</p>{labelGuidance[0] && <a href={labelGuidance[0].source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-700 hover:underline">Official label<ExternalLink size={10} /></a>}</div>}
  </article>;
}

async function requestInteractionCheck(items: string[]) {
  const response = await fetch("/api/interactions/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ medications: items.map((name) => ({ name })) }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Unable to check interactions");
  return payload as CheckResponse;
}

export function InteractionChecker() {
  const [input, setInput] = useState("");
  const [medications, setMedications] = useState<string[]>([]);
  const [pinnedItems, setPinnedItems] = useState<string[]>([]);
  const [pinsLoaded, setPinsLoaded] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [findingFilter, setFindingFilter] = useState<FindingFilter>("all");
  const [catalogSuggestions, setCatalogSuggestions] = useState<string[]>(fallbackSuggestions);
  useEffect(() => {
    let active = true;
    void fetch("/api/interactions/catalog", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((payload: { ingredients?: string[]; products?: string[] }) => {
        if (!active) return;
        setCatalogSuggestions([...new Set([
          ...fallbackSuggestions,
          ...(payload.ingredients ?? []),
          ...(payload.products ?? []),
        ])]);
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);
  const filteredSuggestions = useMemo(() => {
    const query = input.trim().toLowerCase();
    if (!query) return [];
    return catalogSuggestions
      .filter((item) => item.toLowerCase().includes(query) && !medications.some((medication) => medication.toLowerCase() === item.toLowerCase()))
      .sort((left, right) => Number(!left.toLowerCase().startsWith(query)) - Number(!right.toLowerCase().startsWith(query)) || left.length - right.length || left.localeCompare(right))
      .slice(0, 10);
  }, [catalogSuggestions, input, medications]);
  const findings = result ? [...result.interactions, ...result.timing_restrictions, ...result.food_interactions, ...result.beverage_interactions] : [];
  const preliminaryFindings = result?.preliminary_findings ?? [];
  // A product label can contain warnings about another active ingredient in a
  // combination product. Do not turn that into a pair claim unless the passage
  // actually names both selected substances.
  const labelMentions = (result?.label_mentions ?? []).filter(passageNamesBothSides);
  const visibleRules = dedupeRules([...findings, ...preliminaryFindings, ...labelMentions])
    .filter((rule) => !isNonInteractionFinding(rule) && findingSummary(rule) !== null);
  const filteredRules = visibleRules.filter((rule) => {
    if (findingFilter === "all") return true;
    if (findingFilter === "timing") return rule.interaction_type === "timing_separation";
    if (findingFilter === "food") return rule.interaction_type === "drug_food";
    if (findingFilter === "drink") return rule.interaction_type === "drug_beverage";
    return !["timing_separation", "drug_food", "drug_beverage"].includes(rule.interaction_type);
  });
  const warningCount = visibleRules.length;
  const categoryCounts: Record<Exclude<FindingFilter, "all">, number> = {
    together: visibleRules.filter((rule) => !["timing_separation", "drug_food", "drug_beverage"].includes(rule.interaction_type)).length,
    timing: visibleRules.filter((rule) => rule.interaction_type === "timing_separation").length,
    food: visibleRules.filter((rule) => rule.interaction_type === "drug_food").length,
    drink: visibleRules.filter((rule) => rule.interaction_type === "drug_beverage").length,
  };
  const populatedCategoryCount = Object.values(categoryCounts).filter((count) => count > 0).length;
  const availableFilters = findingFilters.filter((filter) => filter.key === "all" || (populatedCategoryCount > 1 && categoryCounts[filter.key] > 0));
  const showFindingFilters = warningCount > 1 && populatedCategoryCount > 1;
  const sectionTitle = findingFilter === "timing"
    ? "Timing and separation"
    : findingFilter === "food"
      ? "Food interactions"
      : findingFilter === "drink"
        ? "Drink interactions"
        : findingFilter === "together" || categoryCounts.together === warningCount
          ? "Medication interactions"
          : "Interaction findings";

  useEffect(() => {
    let pins: string[] = [];
    let cancelled = false;
    try {
      const stored = JSON.parse(window.localStorage.getItem(PINNED_ITEMS_KEY) ?? "[]");
      if (Array.isArray(stored)) {
        pins = stored.filter((item): item is string => typeof item === "string");
      }
    } catch {
      window.localStorage.removeItem(PINNED_ITEMS_KEY);
    }
    queueMicrotask(() => {
      if (cancelled) return;
      setPinnedItems(pins);
      setMedications(pins);
      setPinsLoaded(true);
      if (pins.length >= 1) {
        setLoading(true);
        void requestInteractionCheck(pins)
          .then((payload) => { if (!cancelled) setResult(payload); })
          .catch((caught) => { if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to check interactions"); })
          .finally(() => { if (!cancelled) setLoading(false); });
      }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (pinsLoaded) window.localStorage.setItem(PINNED_ITEMS_KEY, JSON.stringify(pinnedItems));
  }, [pinnedItems, pinsLoaded]);

  function guidanceForMedication(medication: CheckResponse["medications"][number]) {
    return result?.label_guidance.filter((label) => medication.ingredient_ids.includes(label.ingredient_id)) ?? [];
  }

  async function runCheck(next: string[]) {
    setMedications(next);
    setFindingFilter("all");
    setResult(null);
    setError("");
    if (next.length < 1) return;
    setLoading(true);
    try {
      setResult(await requestInteractionCheck(next));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to check interactions");
    } finally {
      setLoading(false);
    }
  }

  function addMedication(event?: FormEvent) {
    event?.preventDefault();
    const value = input.trim();
    if (!value || medications.some((item) => item.toLowerCase() === value.toLowerCase())) return;
    setInput("");
    void runCheck([...medications, value]);
  }

  function togglePin(item: string) {
    setPinnedItems((current) => current.some((value) => value.toLowerCase() === item.toLowerCase())
      ? current.filter((value) => value.toLowerCase() !== item.toLowerCase())
      : [...current, item]);
  }

  function removeMedication(item: string) {
    setPinnedItems((current) => current.filter((value) => value.toLowerCase() !== item.toLowerCase()));
    void runCheck(medications.filter((value) => value !== item));
  }

  function renderMedicationSearch() {
    return <form onSubmit={addMedication} className="w-full">
      <div className="relative min-w-0 rounded-[32px] border border-slate-200 bg-white px-6 py-3 shadow-[0_8px_28px_rgba(15,23,42,0.08)] transition focus-within:border-slate-300 focus-within:shadow-[0_10px_32px_rgba(15,23,42,0.12)]">
        <Search size={21} className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-500" />
        <input id="compatibility-search" aria-label="Search medicines, supplements, food, or drinks" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Type aspirin, vitamin D, grapefruit, coffee…" autoComplete="off" className="h-11 w-full bg-transparent pl-9 pr-3 text-[16px] font-medium text-text-primary outline-none placeholder:font-normal placeholder:text-slate-400" />
        {filteredSuggestions.length > 0 && <div className="absolute inset-x-0 top-[76px] z-20 overflow-hidden rounded-[16px] border border-border bg-white text-left shadow-lg">{filteredSuggestions.map((item) => <button key={item} type="button" onClick={() => { setInput(""); void runCheck([...medications, item]); }} className="block w-full px-5 py-3 text-left text-[13px] font-medium hover:bg-orange-50">{item}</button>)}</div>}
      </div>
    </form>;
  }

  return <main className="mx-auto w-full max-w-[1440px] flex-1 px-5 py-5 sm:px-8 lg:px-10">
    {medications.length === 0 ? <section className="grid min-h-[calc(100vh-170px)] place-items-center px-4 py-10 text-center"><div className="w-full max-w-[900px] -translate-y-6 sm:-translate-y-8"><ShieldAlert size={36} className="mx-auto text-slate-300" /><h1 className="mt-3 text-[24px] font-extrabold text-brand-navy">What would you like to check?</h1><div className="mx-auto mt-5 flex max-w-[760px] flex-wrap justify-center gap-2">{[{ icon: Link2, title: "Take together?", tone: "text-brand-coral" }, { icon: Clock3, title: "Separate by time?", tone: "text-violet-600" }, { icon: Utensils, title: "With food?", tone: "text-emerald-600" }, { icon: Wine, title: "With drinks?", tone: "text-sky-600" }].map(({ icon: Icon, title, tone }) => <span key={title} className="inline-flex items-center gap-2 rounded-pill bg-white px-4 py-2.5 text-[12px] font-bold text-brand-navy shadow-sm"><Icon size={16} className={tone} />{title}</span>)}</div><div className="mx-auto mt-7">{renderMedicationSearch()}</div></div></section> : <>
    <section className="rounded-[28px] bg-white p-3 shadow-card sm:p-4">
      {renderMedicationSearch()}
      <div className="mt-4 flex min-h-9 flex-wrap gap-2">{medications.map((medication) => {
        const pinned = pinnedItems.some((item) => item.toLowerCase() === medication.toLowerCase());
        return <span key={medication} className={`inline-flex items-center gap-2 rounded-pill border px-3 py-2 text-[12px] font-bold capitalize ${pinned ? "border-brand-coral bg-brand-coral text-white" : "border-transparent bg-surface-muted text-text-primary"}`}><Link2 size={13} className="-rotate-45" />{medication}<button type="button" aria-label={pinned ? `Unpin ${medication}` : `Pin ${medication}`} title={pinned ? "Unpin" : "Keep in future checks"} onClick={() => togglePin(medication)} className={pinned ? "text-white/80 hover:text-white" : "text-slate-400 hover:text-brand-coral"}>{pinned ? <PinOff size={13} /> : <Pin size={13} />}</button><button type="button" aria-label={`Remove ${medication}`} onClick={() => removeMedication(medication)} className={pinned ? "text-white/80 hover:text-white" : "text-slate-400 hover:text-brand-coral"}><X size={13} /></button></span>;
      })}</div>
    </section>

    <div className="mt-6 grid items-start gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="rounded-card bg-white p-4 shadow-card"><div className="flex items-center justify-between gap-2"><h2 className="text-[15px] font-extrabold">Your check</h2>{pinnedItems.length > 0 && <span className="inline-flex items-center gap-1 text-[10px] font-bold text-brand-coral"><Pin size={11} />{pinnedItems.length} pinned</span>}</div><div className="mt-3 divide-y divide-border">{medications.map((medication) => {
        const pinned = pinnedItems.some((item) => item.toLowerCase() === medication.toLowerCase());
        return <div key={medication} className="flex items-center gap-3 py-3"><span className={`grid size-9 place-items-center rounded-full ${pinned ? "bg-orange-100 text-brand-coral" : "bg-surface-muted text-brand-navy"}`}><Link2 size={16} className="-rotate-45" /></span><span className="min-w-0 flex-1 truncate text-[13px] font-semibold capitalize">{medication}</span><button type="button" onClick={() => togglePin(medication)} aria-label={pinned ? `Unpin ${medication}` : `Pin ${medication}`} title={pinned ? "Unpin" : "Keep in future checks"} className={pinned ? "text-brand-coral" : "text-slate-400 hover:text-brand-coral"}>{pinned ? <PinOff size={14} /> : <Pin size={14} />}</button><button type="button" onClick={() => removeMedication(medication)} aria-label={`Remove ${medication}`}><X size={14} className="text-slate-400" /></button></div>;
      })}</div></aside>

      <section className="min-h-[460px] rounded-card bg-white p-5 shadow-card">
        {loading ? <div className="grid min-h-[410px] place-items-center text-center"><div><Loader2 size={30} className="mx-auto animate-spin text-slate-400" /><p className="mt-3 text-[13px] font-semibold">Checking reviewed interaction rules…</p></div></div>
        : error ? <div className="grid min-h-[410px] place-items-center text-center"><div><AlertTriangle size={32} className="mx-auto text-rose-500" /><h2 className="mt-3 font-extrabold">Check unavailable</h2><p className="mt-2 text-[13px] text-text-secondary">{error}</p></div></div>
        : result ? <div>
          {showFindingFilters && <div className="mb-5 flex flex-wrap gap-2" aria-label="Filter interaction findings">
            {availableFilters.map((filter) => {
              const Icon = filter.icon;
              const active = findingFilter === filter.key;
              const count = filter.key === "all" ? warningCount : categoryCounts[filter.key];
              return <button key={filter.key} type="button" onClick={() => setFindingFilter(filter.key)} aria-pressed={active} className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-2 text-[11px] font-bold transition ${active ? "border-brand-navy bg-brand-navy text-white" : "border-border bg-white text-text-secondary hover:border-brand-navy hover:text-brand-navy"}`}><Icon size={13} />{filter.label}{count > 0 && <span className={active ? "text-white/70" : "text-text-tertiary"}>{count}</span>}</button>;
            })}
          </div>}
          {warningCount ? <section>
            <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-[17px] font-extrabold text-brand-navy">{sectionTitle}</h2>{warningCount > 1 && <span className="rounded-pill bg-amber-50 px-3 py-1.5 text-[11px] font-bold text-amber-700">{showFindingFilters ? `${filteredRules.length} shown · ${warningCount} total` : `${warningCount} findings`}</span>}</div>
            {filteredRules.length ? <div className="mt-3 space-y-3">{filteredRules.map((rule) => <FindingCard key={ruleKey(rule)} rule={rule} />)}</div> : <div className="mt-3 rounded-[14px] bg-slate-50 p-5 text-center text-[12px] text-text-tertiary">No findings in this category for the items you added.</div>}
          </section> : medications.length > 1 ? <div className="rounded-[16px] bg-emerald-50 p-4"><div className="flex items-start gap-3"><CheckCircle2 size={20} className="mt-0.5 shrink-0 text-emerald-600" /><div><p className="text-[11px] font-extrabold uppercase tracking-[0.05em] text-emerald-700">No specific interaction found</p><p className="mt-1 text-[13px] leading-5 text-text-secondary">No interaction was identified in the available official labels. This does not guarantee the combination is safe.</p></div></div></div> : null}
          <section className="mt-6"><h2 className="text-[15px] font-extrabold text-brand-navy">Medication guidance</h2><div className="mt-3 space-y-3">{result.medications.filter((medication) => medication.resolution !== "supported_food_or_drink").map((medication) => <MedicationSummaryCard key={medication.input_name} medication={medication} labelGuidance={guidanceForMedication(medication)} />)}</div></section>
        </div> : null}
      </section>

    </div>
    <p className="mt-4 text-center text-[11px] leading-5 text-text-tertiary">Results link to NIH ODS, FDA, or DailyMed sources. Do not stop or change a prescribed medicine without speaking with your clinician.</p>
    </>}
  </main>;
}
