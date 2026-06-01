"""Inline label/value segmentation for static text and OCR output."""

from __future__ import annotations

import re
from typing import Any

from .signal_evidence_anchors import trim_span
from .signal_multilingual_labels import multilingual_label_tokens

EXPLICIT_LABEL_SEPARATOR_RE = r"[:：#]|[-–—]"
VALUE_TRAILING_DELIMITERS = " \t;,|"

INLINE_LABEL_ALIASES = tuple(sorted({
    "account id",
    "account number",
    "address",
    "advertising id",
    "allergy",
    "amount",
    "api key",
    "approver",
    "bank account",
    "bic",
    "birth date",
    "bonus",
    "card number",
    "citizen id",
    "comment",
    "compensation",
    "contact person",
    "cookie",
    "cookie id",
    "corrective action",
    "credit card",
    "date of birth",
    "deadline",
    "department",
    "device id",
    "diagnosis",
    "dob",
    "driver license",
    "driving licence",
    "email",
    "emergency contact",
    "employee id",
    "evaluation",
    "expense",
    "feedback",
    "full name",
    "government id",
    "guardian",
    "health insurance",
    "home address",
    "iban",
    "identity number",
    "imei",
    "incident",
    "insurance id",
    "ip address",
    "justification",
    "latitude",
    "license number",
    "location",
    "longitude",
    "manager",
    "medical condition",
    "medical record",
    "mobile",
    "name",
    "national id",
    "next of kin",
    "nhs number",
    "passport",
    "passport number",
    "password",
    "patient id",
    "payroll",
    "personnel number",
    "phone",
    "postal address",
    "profile id",
    "recommendation",
    "reimbursement",
    "reported by",
    "requester",
    "resident permit",
    "reviewer",
    "role",
    "salary",
    "secret",
    "serial number",
    "signature",
    "social security",
    "ssn",
    "staff id",
    "street address",
    "student id",
    "student number",
    "swift",
    "tax id",
    "telephone",
    "token",
    "tracking id",
    "username",
    "vat id",
    "visa number",
    "worker id",
    *multilingual_label_tokens(),
}, key=len, reverse=True))
INLINE_LABEL_PATTERN = "|".join(re.escape(label) for label in INLINE_LABEL_ALIASES)
INLINE_EXPLICIT_LABEL_RE = re.compile(
    rf"(?P<label>{INLINE_LABEL_PATTERN})\s*(?P<separator>{EXPLICIT_LABEL_SEPARATOR_RE})\s*",
    re.IGNORECASE,
)
INLINE_WHITESPACE_LABEL_RE = re.compile(
    rf"(?P<label>{INLINE_LABEL_PATTERN})(?=\s+\S)",
    re.IGNORECASE,
)
INLINE_SEPARATORLESS_LABEL_RE = re.compile(
    rf"(?P<label>{INLINE_LABEL_PATTERN})",
    re.IGNORECASE,
)


def inline_label_value_spans(line: str) -> list[tuple[str, int, int]]:
    matches = _inline_label_matches(line)
    spans: list[tuple[str, int, int]] = []
    for index, match in enumerate(matches):
        value_start = match["value_start"]
        value_end = matches[index + 1]["label_start"] if index + 1 < len(matches) else len(line)
        value_start, value_end = _trim_value_span(line, value_start, value_end)
        if value_start < value_end:
            spans.append((match["label"], value_start, value_end))
    return spans


def _inline_label_matches(line: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for regex in (INLINE_EXPLICIT_LABEL_RE, INLINE_WHITESPACE_LABEL_RE, INLINE_SEPARATORLESS_LABEL_RE):
        for match in regex.finditer(line):
            label = _clean_label(match.group("label"))
            if regex is INLINE_WHITESPACE_LABEL_RE and not _label_allows_whitespace_separator(label):
                continue
            if regex is INLINE_SEPARATORLESS_LABEL_RE and not _label_allows_separatorless_value(label):
                continue
            if _overlaps(match.start(), match.end(), occupied):
                continue
            if not _has_label_boundary(line, match.start(), match.end("label")):
                continue
            occupied.append((match.start(), match.end()))
            matches.append({
                "label": label,
                "label_start": match.start(),
                "value_start": match.end(),
            })
    matches.sort(key=lambda item: item["label_start"])
    return matches


def _trim_value_span(line: str, start: int, end: int) -> tuple[int, int]:
    start, end = trim_span(line, start, end)
    while end > start and line[end - 1] in VALUE_TRAILING_DELIMITERS:
        end -= 1
    return trim_span(line, start, end)


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()


def _label_allows_whitespace_separator(label: str) -> bool:
    return _contains_cjk_kana_hangul_or_arabic(label)


def _label_allows_separatorless_value(label: str) -> bool:
    return _contains_cjk_kana_or_hangul(label)


def _contains_cjk_kana_hangul_or_arabic(value: str) -> bool:
    return any(
        "\u4e00" <= character <= "\u9fff"
        or "\u3040" <= character <= "\u30ff"
        or "\uac00" <= character <= "\ud7af"
        or "\u0600" <= character <= "\u06ff"
        for character in value
    )


def _contains_cjk_kana_or_hangul(value: str) -> bool:
    return any(
        "\u4e00" <= character <= "\u9fff"
        or "\u3040" <= character <= "\u30ff"
        or "\uac00" <= character <= "\ud7af"
        for character in value
    )


def _has_label_boundary(line: str, start: int, label_end: int) -> bool:
    if start > 0 and _is_word_character(line[start - 1]) and _is_word_character(line[start]):
        return False
    if label_end < len(line) and _is_word_character(line[label_end - 1]) and _is_word_character(line[label_end]):
        return False
    return True


def _is_word_character(character: str) -> bool:
    return character.isascii() and (character.isalnum() or character == "_")


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(used_start < end and start < used_end for used_start, used_end in occupied)
