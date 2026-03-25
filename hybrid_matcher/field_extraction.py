from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from dateutil import parser as date_parser
from rapidfuzz import fuzz


REFERENCE_RE = re.compile(r"\b[A-Z0-9]{1,6}-\d{4,6}(?:-[A-Z]{1,4})?\b")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
    re.IGNORECASE,
)
MONEY_RE = re.compile(r"(?:£|\bGBP\b)?\s*(\d[\d,]*\.\d{2})")
DOC_PATTERNS = [
    re.compile(r"\bInvoice\s+Number[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bInvoice\s+No\.?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bDelivery\s+Note(?:\s+No\.?|\s+number)?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bDelivery\s+no\.?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bDocument\s+No\.?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bJob\s+No\.?[:\s]+([A-Z0-9-]{3,})", re.IGNORECASE),
]
REFERENCE_PATTERNS = [
    re.compile(r"\bCustomer\s+Order\s+No\.?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bOrder\s+Ref[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bOrder\s+Number[:\s-]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bYour\s+ref(?:erence)?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
    re.compile(r"\bOrder\s+No\.?[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE),
]
TOTAL_PATTERNS = [
    re.compile(r"\bInvoice\s+Total\b[^0-9£]*£?\s*(\d[\d,]*\.\d{2})", re.IGNORECASE),
    re.compile(r"\bTotal\s+Payable\b[^0-9£]*£?\s*(\d[\d,]*\.\d{2})", re.IGNORECASE),
    re.compile(r"\bGross\s+Total\b[^0-9£]*£?\s*(\d[\d,]*\.\d{2})", re.IGNORECASE),
    re.compile(r"\bNet\s+Total\b[^0-9£]*£?\s*(\d[\d,]*\.\d{2})", re.IGNORECASE),
]
COMPANY_HINTS = (
    " ltd",
    " limited",
    " llp",
    " plc",
    " inc",
    " corporation",
    " express",
    " glass",
    " hardware",
    " laser",
)
STOP_COMPANY_WORDS = {
    "task corporation ltd",
    "task corporation limited",
    "task corporation ltd.",
    "taskcorp",
}
INVALID_DOCUMENT_NUMBERS = {
    "INVOICE",
    "DELIVERY",
    "DATE",
    "LINE",
    "PAGE",
    "YOUR",
    "PRODUCT",
    "TOTAL",
}
LINE_SKIP_WORDS = {
    "invoice",
    "delivery note",
    "page ",
    "vat ",
    "bank",
    "telephone",
    "email",
    "www.",
    "address",
}


@dataclass
class ExtractedFields:
    document_number: str | None = None
    reference_numbers: list[str] = field(default_factory=list)
    primary_date: date | None = None
    date_strings: list[str] = field(default_factory=list)
    total_amount: float | None = None
    company_name: str | None = None
    line_fragments: list[str] = field(default_factory=list)
    reference_tokens: list[str] = field(default_factory=list)


def normalize_code(value: str) -> str:
    value = value.strip().upper()
    value = re.sub(r"\s+", "", value)
    value = value.rstrip(".,:;")
    return value


def normalize_company_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:").lower()


def extract_fields(text: str, lines: Iterable[str]) -> ExtractedFields:
    fields = ExtractedFields()
    fields.document_number = extract_document_number(text)
    fields.reference_numbers = extract_reference_numbers(text)
    fields.reference_tokens = extract_reference_tokens(text)
    fields.primary_date, fields.date_strings = extract_dates(text)
    fields.total_amount = extract_total_amount(text)
    fields.company_name = extract_company_name(lines)
    fields.line_fragments = extract_line_fragments(lines)
    return fields


def extract_document_number(text: str) -> str | None:
    for pattern in DOC_PATTERNS:
        match = pattern.search(text)
        if match:
            value = normalize_code(match.group(1))
            if value not in INVALID_DOCUMENT_NUMBERS:
                return value
    return None


def extract_reference_numbers(text: str) -> list[str]:
    values = []
    for pattern in REFERENCE_PATTERNS:
        values.extend(normalize_code(match.group(1)) for match in pattern.finditer(text))
    values.extend(normalize_code(value) for value in REFERENCE_RE.findall(text))
    return dedupe_preserving_order(values)


def extract_reference_tokens(text: str) -> list[str]:
    codes = [normalize_code(value) for value in REFERENCE_RE.findall(text)]
    return dedupe_preserving_order(codes)


def extract_dates(text: str) -> tuple[date | None, list[str]]:
    raw_dates = dedupe_preserving_order(match.group(0) for match in DATE_RE.finditer(text))
    parsed_dates: list[date] = []
    for raw in raw_dates:
        try:
            parsed_dates.append(date_parser.parse(raw, dayfirst=True, fuzzy=True).date())
        except Exception:
            continue
    primary = parsed_dates[0] if parsed_dates else None
    return primary, raw_dates


def extract_total_amount(text: str) -> float | None:
    for pattern in TOTAL_PATTERNS:
        match = pattern.search(text)
        if match:
            return parse_amount(match.group(1))
    return None


def extract_company_name(lines: Iterable[str]) -> str | None:
    candidates = []
    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()
        lowered = clean.lower()
        if len(clean) < 4 or any(word in lowered for word in LINE_SKIP_WORDS):
            continue
        if sum(char.isdigit() for char in clean) > 6:
            continue
        if "registered in england" in lowered or "company number" in lowered:
            continue
        if any(hint in lowered for hint in COMPANY_HINTS):
            normalized = normalize_company_name(clean)
            if normalized not in STOP_COMPANY_WORDS:
                candidates.append(clean)

    if candidates:
        return candidates[0]
    return None


def extract_line_fragments(lines: Iterable[str], limit: int = 8) -> list[str]:
    fragments = []
    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()
        lowered = clean.lower()
        if len(clean) < 18 or len(clean) > 180:
            continue
        if any(word in lowered for word in LINE_SKIP_WORDS):
            continue
        alpha_words = sum(token.isalpha() for token in clean.split())
        if alpha_words < 2:
            continue
        if clean.count(" ") < 2:
            continue
        fragments.append(clean)
    return fragments[:limit]


def company_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return fuzz.token_sort_ratio(normalize_company_name(left), normalize_company_name(right)) / 100.0


def parse_amount(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
