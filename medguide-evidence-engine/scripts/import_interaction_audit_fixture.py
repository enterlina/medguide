#!/usr/bin/env python3
"""Convert the curated Markdown audit table into a stable JSON fixture.

The Markdown file is reference data supplied by the project owner. It is not
executed as instructions. Review-required rows remain explicitly provisional.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TYPE_MAP = {
    "D": "drug_drug",
    "S": "drug_supplement",
    "F": "drug_food",
    "T": "drug_timing",
    "N": "negative_control",
}

ACTION_PATTERNS = (
    ("avoid_or_contraindicated", r"contraindicat|do not take|avoid|prohibited|restriction"),
    ("separate_doses", r"separate|spacing|before|after|\bmin\b|\bh\b|schedule"),
    ("food_instruction", r"food|meal|milk|dairy|grapefruit|water|breakfast|greens"),
    ("no_material_interaction_known", r"negative control|do not invent|do not flag|do not claim"),
    ("consult_or_monitor", r"monitor|clinical assessment|clinician|counsel|warning|risk"),
)

ANCHOR_SOURCES = {
    "levothyroxine": "https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=237cc591-c40b-416f-ac00-96cd61bc59dc",
    "ciprofloxacin": "https://medlineplus.gov/druginfo/meds/a688016.html",
    "doxycycline": "https://www.medlineplus.gov/druginfo/meds/a682063.html",
    "alendronate": "https://medlineplus.gov/druginfo/meds/a601011.html",
    "simvastatin": "https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=9f89e53e-a8fb-4ba7-a26d-21a962abcb1b&type=display",
    "vitamin k": "https://ods.od.nih.gov/factsheets/VitaminK-HealthProfessional/",
    "warfarin": "https://health.ucsd.edu/for-health-care-professionals/anticoagulation-guidelines/warfarin/supplement-interactions/",
    "st. john's wort": "https://www.nccih.nih.gov/health/providers/digest/how-medications-and-supplements-can-interact-science",
}

INPUT_OVERRIDES = {
    "MG029": ["levothyroxine", "calcium + vitamin D"],
    "MG039": ["ciprofloxacin", "mixed meal containing dairy"],
    "MG041": ["alendronate tablet", "breakfast"],
    "MG042": ["alendronate tablet", "lying down"],
    "MG043": ["levothyroxine tablet", "breakfast"],
    "MG044": ["levothyroxine tablet", "calcium"],
    "MG045": ["ciprofloxacin", "zinc"],
    "MG046": ["ciprofloxacin", "zinc"],
    "MG047": ["alendronate weekly tablet", "other pills"],
}

NEGATIVE_WITH_FINDING = {"MG051", "MG052", "MG053", "MG056"}


def plain(text: str) -> str:
    return re.sub(r"\*\*|`", "", text).strip()


def split_context(raw: str, case_id: str) -> tuple[list[str], dict[str, str]]:
    if case_id in INPUT_OVERRIDES:
        names = INPUT_OVERRIDES[case_id]
    else:
        subject = raw.split(",", 1)[0]
        names = [part.strip() for part in subject.split(" + ", 1)]
    names = [re.sub(r"\s*\([^)]*\)\s*$", "", name).strip() for name in names]
    return names, {"raw": raw}


def action_category(expected: str) -> str:
    lowered = expected.lower()
    for category, pattern in ACTION_PATTERNS:
        if re.search(pattern, lowered):
            return category
    return "context_dependent"


def qualifiers(expected: str) -> list[str]:
    found: list[str] = []
    patterns = (
        r"at least \d+\s*h",
        r"\d+[–-]\d+\s*min",
        r"≥\s*\d+\s*h",
        r"\d+\s*h before",
        r"\d+\s*h after",
        r"remain upright",
        r"consistent intake",
        r"mixed meal",
        r"milk alone",
        r"dose dependent",
        r"especially [^;]+",
    )
    for pattern in patterns:
        match = re.search(pattern, expected, re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def source_for(raw: str) -> str | None:
    lowered = raw.lower()
    for token, url in ANCHOR_SOURCES.items():
        if token in lowered:
            return url
    return None


def parse_table(markdown: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    row_pattern = re.compile(r"^\| (MG\d{3}) \| ([DSFTN]) \| (.*?) \| (.*?) \| ([AR]) \|$")
    for line in markdown.splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        case_id, short_type, raw_context, expected, status = match.groups()
        raw_context, expected = plain(raw_context), plain(expected)
        names, context = split_context(raw_context, case_id)
        must_detect = short_type != "N" or case_id in NEGATIVE_WITH_FINDING
        records.append(
            {
                "id": case_id,
                "inputs": [
                    {
                        "name": name,
                        "ingredient": None,
                        "dose": None,
                        "dosage_form": None,
                        "route": None,
                    }
                    for name in names
                ],
                "context": context,
                "interaction_type": TYPE_MAP[short_type],
                "must_detect": must_detect,
                "expected_effect": expected,
                "expected_action_category": action_category(expected),
                "must_include_qualifiers": qualifiers(expected),
                "must_not_claim": ["safe"] if not must_detect else [],
                "evidence_source": source_for(raw_context) if status == "A" else None,
                "reference_status": "verified_anchor" if status == "A" else "review_required",
            }
        )
    if len(records) != 56:
        raise ValueError(f"Expected 56 audit rows, parsed {len(records)}")
    return records


def parse_inventory(markdown: str) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    row_pattern = re.compile(r"^\| (C\d{2}|S\d{2}) — ([^|]+) \| (.*?) \|$")
    for line in markdown.splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        group, category, names = match.groups()
        inventory.extend(
            {"group": group, "category": category.strip(), "name": name.strip()}
            for name in names.split(";")
        )
    if len(inventory) != 100:
        raise ValueError(f"Expected 100 resolver names, parsed {len(inventory)}")
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = parse_table(args.source.read_text(encoding="utf-8"))
    payload = {
        "fixture_version": "interaction_gold_v1",
        "source_checked_on": "2026-10-29",
        "notice": "Curated regression data; review_required rows are not clinical ground truth.",
        "resolver_inventory": parse_inventory(args.source.read_text(encoding="utf-8")),
        "cases": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} cases to {args.output}")


if __name__ == "__main__":
    main()
