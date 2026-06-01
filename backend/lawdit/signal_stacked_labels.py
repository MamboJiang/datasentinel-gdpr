"""Stacked label/value detection for OCR and form-like text."""

from __future__ import annotations

import unicodedata
from typing import Any, Callable, Iterator

from .signal_evidence_anchors import text_position_anchor, trim_span
from .signal_label_rules import rule_for_label
from .signal_multilingual_labels import multilingual_label_tokens

STACKED_LABEL_TRAILING = ":：#=-–—"
STACKED_LABEL_MAX_WORDS = 6
STACKED_LABEL_ALIASES = {
    "account id",
    "account number",
    "address",
    "api key",
    "bank account",
    "bic",
    "birth date",
    "card number",
    "contact person",
    "credit card",
    "date of birth",
    "device id",
    "driver license",
    "driving licence",
    "email",
    "email address",
    "employee id",
    "full name",
    "government id",
    "home address",
    "iban",
    "identity number",
    "imei",
    "itinerary id",
    "license number",
    "login id",
    "mobile",
    "name",
    "national id",
    "passport",
    "passport number",
    "password",
    "patient id",
    "person name",
    "phone",
    "phone number",
    "postal address",
    "reservation code",
    "signature",
    "social security",
    "ssn",
    "street address",
    "tax id",
    "telephone",
    "ticket number",
    "token",
    "travel booking",
    "traveler",
    "traveller",
    "username",
    "vat id",
    "visa number",
    *multilingual_label_tokens(),
}
STACKED_LABEL_SIGNAL_TYPES = {
    "account_handle",
    "address",
    "bank_account",
    "biometric_data",
    "credential_secret",
    "date_of_birth",
    "device_identifier",
    "driver_license",
    "email",
    "genetic_data",
    "government_identifier",
    "health_data",
    "iban_like",
    "medical_identifier",
    "minor_data",
    "national_identifier",
    "passport_number",
    "payment_card",
    "person_name",
    "phone_number",
    "signature",
    "student_identifier",
    "tax_id",
    "travel_record",
    "url",
}


def stacked_label_signals(
    lines: list[tuple[str, int, int]],
    has_filled_value: Callable[[str], bool],
) -> Iterator[dict[str, Any]]:
    for index, (line, _line_start, _line_number) in enumerate(lines):
        label = _stacked_label(line)
        if not label:
            continue
        value_record = _next_stacked_value(lines, index + 1)
        if not value_record:
            continue
        value_line, value_line_start, value_line_number = value_record
        value_start, value_end = trim_span(value_line, 0, len(value_line))
        value = value_line[value_start:value_end]
        if not has_filled_value(value):
            continue
        rule = rule_for_label(label, value)
        if not rule or rule.signal_type not in STACKED_LABEL_SIGNAL_TYPES:
            continue
        detector = f"{rule.detector}_stacked"
        snippet = f"{label}: {rule.marker}"
        yield {
            "type": rule.signal_type,
            "detector": detector,
            "confidence": max(0.0, rule.confidence - 0.02),
            "snippet": snippet[:180],
            "page": None,
            "evidenceAnchor": text_position_anchor(
                rule.signal_type,
                detector,
                value_line_start + value_start,
                value_line_start + value_end,
                value_line_number,
                snippet,
            ),
        }


def _next_stacked_value(lines: list[tuple[str, int, int]], start_index: int) -> tuple[str, int, int] | None:
    for value_line, value_start, value_line_number in lines[start_index:start_index + 3]:
        if not value_line.strip():
            continue
        if _stacked_label(value_line):
            return None
        return value_line, value_start, value_line_number
    return None


def _stacked_label(line: str) -> str | None:
    label = line.strip().rstrip(STACKED_LABEL_TRAILING).strip()
    if not label or len(label) > 72:
        return None
    if any(character.isdigit() for character in label):
        return None
    if any(character in label for character in "/\\|{}[]()"):
        return None
    if len(label.split()) > STACKED_LABEL_MAX_WORDS:
        return None
    cleaned = _clean_label(label)
    if _stacked_label_key(cleaned) not in STACKED_LABEL_ALIAS_KEYS:
        return None
    return cleaned


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()


def _stacked_label_key(label: str) -> str:
    decomposed = unicodedata.normalize("NFKD", _clean_label(label)).casefold()
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(without_marks.split())


STACKED_LABEL_ALIAS_KEYS = frozenset(_stacked_label_key(alias) for alias in STACKED_LABEL_ALIASES)
