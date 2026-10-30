from __future__ import annotations

import hashlib
import io
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from app.interactions.models import LabelDocument


OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
DAILYMED_SPLS_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
DAILYMED_SPL_DOWNLOAD_URL = "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm"


class _ODSSectionParser(HTMLParser):
    """Small deterministic parser for ODS fact-sheet headings and readable text."""

    def __init__(self) -> None:
        super().__init__()
        self.heading_level: int | None = None
        self.heading_parts: list[str] = []
        self.current_h2: str | None = None
        self.current_h3: str | None = None
        self.capture_tag: str | None = None
        self.capture_parts: list[str] = []
        self.sections: dict[str, list[str]] = {}

    @staticmethod
    def _key(value: str) -> str:
        return "_".join(value.casefold().replace("&", "and").split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3"}:
            self.heading_level = int(tag[1])
            self.heading_parts = []
        elif self.current_h2 and tag in {"p", "li"} and self.capture_tag is None:
            self.capture_tag = tag
            self.capture_parts = []

    def handle_data(self, data: str) -> None:
        if self.heading_level:
            self.heading_parts.append(data)
        elif self.capture_tag:
            self.capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.heading_level and tag == f"h{self.heading_level}":
            heading = " ".join(" ".join(self.heading_parts).split())
            if self.heading_level == 2:
                self.current_h2 = heading
                self.current_h3 = None
            else:
                self.current_h3 = heading
            self.heading_level = None
            self.heading_parts = []
        elif self.capture_tag == tag:
            text = " ".join(" ".join(self.capture_parts).split())
            if text and self.current_h2:
                if self.current_h3:
                    text = f"{self.current_h3}: {text}"
                self.sections.setdefault(self._key(self.current_h2), []).append(text)
            self.capture_tag = None
            self.capture_parts = []


@dataclass(frozen=True)
class JsonTransport:
    timeout_seconds: float = 30.0
    user_agent: str = "MedGuide interaction-pilot/0.1"

    def get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        request_url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(request_url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)

    def get_bytes(self, url: str, params: dict[str, str]) -> bytes:
        request_url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(request_url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read()


class RxNormResolver:
    def __init__(self, transport: JsonTransport | None = None):
        self.transport = transport or JsonTransport()

    def find_rxcui(self, name: str) -> str | None:
        payload = self.transport.get_json(
            f"{RXNORM_BASE_URL}/rxcui.json", {"name": name, "search": "2"}
        )
        identifiers = payload.get("idGroup", {}).get("rxnormId") or []
        return str(identifiers[0]) if identifiers else None

    def related_ingredients(self, rxcui: str) -> list[dict[str, str]]:
        payload = self.transport.get_json(
            f"{RXNORM_BASE_URL}/rxcui/{urllib.parse.quote(rxcui)}/related.json",
            {"tty": "IN+PIN"},
        )
        groups = payload.get("relatedGroup", {}).get("conceptGroup") or []
        results = []
        for group in groups:
            for concept in group.get("conceptProperties") or []:
                results.append({"rxcui": str(concept["rxcui"]), "name": concept["name"]})
        return results


class OpenFDALabelAdapter:
    SECTION_FIELDS = (
        "drug_interactions",
        "dosage_and_administration",
        "contraindications",
        "warnings",
        "warnings_and_cautions",
        "precautions",
        "pregnancy",
        "pregnancy_or_breast_feeding",
        "use_in_specific_populations",
        "clinical_pharmacology",
        "pharmacokinetics",
        "information_for_patients",
        "instructions_for_use",
        "do_not_use",
        "ask_doctor_or_pharmacist",
    )

    def __init__(self, transport: JsonTransport | None = None):
        self.transport = transport or JsonTransport()

    def fetch_by_rxcui(self, rxcui: str, limit: int = 10) -> list[LabelDocument]:
        payload = self.transport.get_json(
            OPENFDA_LABEL_URL,
            {"search": f"openfda.rxcui:{rxcui}", "limit": str(min(limit, 100))},
        )
        return [self.parse_record(record) for record in payload.get("results", [])]

    def fetch_by_generic_name(self, name: str, limit: int = 10) -> list[LabelDocument]:
        escaped = name.replace('"', "")
        payload = self.transport.get_json(
            OPENFDA_LABEL_URL,
            {
                "search": f'openfda.generic_name:"{escaped}"',
                "limit": str(min(limit, 100)),
            },
        )
        return [self.parse_record(record) for record in payload.get("results", [])]

    @classmethod
    def parse_record(cls, record: dict[str, Any]) -> LabelDocument:
        def first(value: Any) -> Any:
            return value[0] if isinstance(value, list) and value else value

        openfda = record.get("openfda") or {}
        label_id = str(record.get("id") or record.get("set_id") or record.get("effective_time"))
        sections = {
            field: [str(value).strip() for value in record.get(field, []) if str(value).strip()]
            for field in cls.SECTION_FIELDS
            if record.get(field)
        }
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False).encode()
        return LabelDocument(
            label_id=f"openfda:{label_id}",
            source="openfda",
            source_url=f"https://api.fda.gov/drug/label.json?search=id:{urllib.parse.quote(label_id)}",
            set_id=first(record.get("set_id")),
            version=first(record.get("version")),
            effective_time=record.get("effective_time"),
            product_name=first(openfda.get("brand_name") or openfda.get("generic_name")),
            rxcui=first(openfda.get("rxcui")),
            sections=sections,
            content_hash=hashlib.sha256(canonical).hexdigest(),
        )


class DailyMedSPLAdapter:
    SECTION_CODES = {
        "34067-9": "indications_and_usage",
        "34068-7": "dosage_and_administration",
        "34070-3": "contraindications",
        "34073-7": "drug_interactions",
        "43685-7": "warnings_and_precautions",
        "34084-4": "adverse_reactions",
        "43684-0": "use_in_specific_populations",
        "42228-7": "pregnancy",
        "77290-5": "lactation",
        "34081-0": "pediatric_use",
        "34082-8": "geriatric_use",
        "34076-0": "information_for_patients",
        "59845-8": "instructions_for_use",
        "34071-1": "warnings",
        "42232-9": "precautions",
        "34089-3": "description",
    }

    def __init__(self, transport: JsonTransport | None = None):
        self.transport = transport or JsonTransport()

    def list_by_rxcui(self, rxcui: str, page_size: int = 20) -> list[dict[str, Any]]:
        payload = self.transport.get_json(
            DAILYMED_SPLS_URL, {"rxcui": rxcui, "pagesize": str(min(page_size, 100))}
        )
        return payload.get("data", payload.get("spls", []))

    def fetch_spl_xml(self, set_id: str) -> str:
        archive = self.transport.get_bytes(
            DAILYMED_SPL_DOWNLOAD_URL, {"setid": set_id, "type": "zip"}
        )
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            xml_names = [name for name in bundle.namelist() if name.casefold().endswith(".xml")]
            if len(xml_names) != 1:
                raise ValueError("DailyMed SPL archive must contain exactly one XML document")
            return bundle.read(xml_names[0]).decode("utf-8")

    @classmethod
    def parse_xml(cls, xml_text: str, set_id: str, version: str | None = None) -> LabelDocument:
        root = ET.fromstring(xml_text)
        sections: dict[str, list[str]] = {}
        for section in root.findall(".//{*}section"):
            code = section.find("./{*}code")
            section_name = cls.SECTION_CODES.get(code.attrib.get("code", "") if code is not None else "")
            title_node = section.find("./{*}title")
            title = " ".join(" ".join(title_node.itertext()).split()) if title_node is not None else ""
            if not section_name and code is not None and code.attrib.get("code") == "42229-5":
                # DailyMed uses a generic subsection code. Recover the parent label
                # section from the numbered title instead of dropping useful text.
                prefix_map = {
                    "2.": "dosage_and_administration",
                    "5.": "warnings_and_precautions",
                    "6.": "adverse_reactions",
                    "7.": "drug_interactions",
                    "8.1": "pregnancy",
                    "8.2": "lactation",
                    "8.4": "pediatric_use",
                    "8.5": "geriatric_use",
                    "17": "information_for_patients",
                }
                section_name = next(
                    (value for prefix, value in prefix_map.items() if title.startswith(prefix)),
                    None,
                )
            if not section_name:
                continue
            text_node = section.find("./{*}text")
            text = " ".join(" ".join(text_node.itertext()).split()) if text_node is not None else ""
            if text:
                sections.setdefault(section_name, []).append(text)
        digest = hashlib.sha256(xml_text.encode()).hexdigest()
        return LabelDocument(
            label_id=f"dailymed:{set_id}:{version or 'unknown'}",
            source="dailymed",
            source_url=f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
            set_id=set_id,
            version=version,
            sections=sections,
            content_hash=digest,
        )


class NIHODSFactSheetAdapter:
    """Downloads and preserves official NIH ODS health-professional guidance."""

    KEEP_SECTIONS = {
        "recommended_intakes",
        "health_risks_from_excessive_vitamin_d",
        "interactions_with_medications",
    }

    def __init__(self, transport: JsonTransport | None = None):
        self.transport = transport or JsonTransport()

    def fetch(self, slug: str) -> LabelDocument:
        url = f"https://ods.od.nih.gov/factsheets/{slug}-HealthProfessional/"
        request = urllib.request.Request(url, headers={"User-Agent": self.transport.user_agent})
        with urllib.request.urlopen(request, timeout=self.transport.timeout_seconds) as response:
            html = response.read().decode("utf-8")
        return self.parse_html(html, slug, url)

    @classmethod
    def parse_html(cls, html: str, slug: str, source_url: str) -> LabelDocument:
        parser = _ODSSectionParser()
        parser.feed(html)
        sections = {
            name: blocks
            for name, blocks in parser.sections.items()
            if name in cls.KEEP_SECTIONS or name == "interactions_with_medications"
        }
        return LabelDocument(
            label_id=f"nih-ods:{slug.casefold()}",
            source="nih_ods",
            source_url=source_url,
            product_name=slug,
            sections=sections,
            content_hash=hashlib.sha256(html.encode()).hexdigest(),
        )

