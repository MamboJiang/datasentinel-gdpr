"""Deterministic redacted signal detection for prelaunch scans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .signal_inline_labels import inline_label_value_spans
from .signal_label_rules import rule_for_label
from .signal_evidence_anchors import (
    display_type,
    line_number as source_line_number,
    safe_public_source_path,
    sanitize_public_signal,
    text_position_anchor,
    trim_span,
)

MAX_SIGNAL_SCAN_CHARS = 200_000
MAX_SIGNALS_PER_DOCUMENT = 32

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b")
PHONE_RE = re.compile(r"\b(?:\+\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?){2,4}\d{2,4}\b")
EMPLOYEE_ID_RE = re.compile(r"\b(?:EMP|EE|E)-\d{3,8}\b", re.IGNORECASE)
TAX_ID_RE = re.compile(r"\b(?:tax|vat)\s*id\s*[:#]?\s*[A-Z0-9 -]{6,20}\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"\b(?:EUR|USD|GBP|CHF)\s?\d{1,6}(?:[,.]\d{2})?\b|\b\d{1,6}(?:[,.]\d{2})\s?(?:EUR|USD|GBP|CHF)\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
UK_NINO_RE = re.compile(r"\b(?!BG|GB|KN|NK|NT|TN|ZZ)[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", re.IGNORECASE)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
UUID_RE = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}\b")
PAYMENT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
GEO_COORD_RE = re.compile(r"\b[-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?)\s*,\s*[-+]?(?:1[0-7]\d(?:\.\d+)?|[1-9]?\d(?:\.\d+)?|180(?:\.0+)?)\b")
URL_RE = re.compile(r"\bhttps?://[^\s<>()\"']{6,}\b", re.IGNORECASE)
USERNAME_RE = re.compile(r"(?<![A-Za-z0-9._%+-])@[A-Za-z0-9_]{3,30}\b")
DATE_LIKE_RE = re.compile(r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b")
LABEL_RE = re.compile(r"^\s*(?P<label>[^:：\r\n]{1,72})\s*[:：]\s*(?P<value>.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"^[\s._/\\|()[\]{}-]+$")


@dataclass(frozen=True)
class RegexRule:
    signal_type: str
    detector: str
    marker: str
    pattern: re.Pattern[str]
    confidence: float
    validator: Callable[[str], bool] | None = None


REGEX_RULES = (
    RegexRule("email", "email_pattern", "[REDACTED_EMAIL]", EMAIL_RE, 0.91),
    RegexRule("iban_like", "iban_like_pattern", "[REDACTED_FINANCIAL_ID]", IBAN_RE, 0.91),
    RegexRule("phone_number", "phone_number_pattern", "[REDACTED_PHONE]", PHONE_RE, 0.88, lambda value: _valid_phone(value)),
    RegexRule("employee_id", "employee_id_pattern", "[REDACTED_EMPLOYEE_ID]", EMPLOYEE_ID_RE, 0.87),
    RegexRule("tax_id", "tax_id_pattern", "[REDACTED_TAX_ID]", TAX_ID_RE, 0.84),
    RegexRule("expense_amount", "currency_amount_pattern", "[REDACTED_AMOUNT]", AMOUNT_RE, 0.82),
    RegexRule("national_identifier", "ssn_pattern", "[REDACTED_NATIONAL_ID]", SSN_RE, 0.88),
    RegexRule("national_identifier", "uk_nino_pattern", "[REDACTED_NATIONAL_ID]", UK_NINO_RE, 0.83),
    RegexRule("online_identifier", "ipv4_pattern", "[REDACTED_IP_ADDRESS]", IPV4_RE, 0.8, lambda value: _valid_ipv4(value)),
    RegexRule("online_identifier", "ipv6_pattern", "[REDACTED_IP_ADDRESS]", IPV6_RE, 0.76),
    RegexRule("device_identifier", "mac_address_pattern", "[REDACTED_DEVICE_ID]", MAC_RE, 0.84),
    RegexRule("online_identifier", "uuid_pattern", "[REDACTED_ONLINE_ID]", UUID_RE, 0.76),
    RegexRule("payment_card", "payment_card_luhn_pattern", "[REDACTED_PAYMENT_CARD]", PAYMENT_CARD_RE, 0.9, lambda value: _valid_payment_card(value)),
    RegexRule("location_data", "geo_coordinate_pattern", "[REDACTED_LOCATION]", GEO_COORD_RE, 0.82),
    RegexRule("url", "url_pattern", "[REDACTED_URL]", URL_RE, 0.68, lambda value: _url_has_personal_hint(value)),
    RegexRule("account_handle", "account_handle_pattern", "[REDACTED_HANDLE]", USERNAME_RE, 0.7),
)

WEAKER_OVERLAP_SUPPRESSIONS = {
    "expense_amount": {"salary_compensation"},
    "iban_like": {"bank_account"},
    "phone_number": {
        "bank_account",
        "date_of_birth",
        "employee_id",
        "national_identifier",
        "passport_number",
        "payment_card",
        "tax_id",
    },
}

def detect_signals(text: str) -> list[dict[str, Any]]:
    """Return public-safe signal records without raw adjacent source context."""
    scanned_text = text[:MAX_SIGNAL_SCAN_CHARS]
    signals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    line_start = 0
    current_line_number = 1
    for line in scanned_text.splitlines(keepends=True):
        visible_line = line.rstrip("\r\n")
        for label_signal in _signals_from_label_line(visible_line, line_start, current_line_number):
            _append_signal(signals, seen, label_signal)
            if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
                return signals
        line_start += len(line)
        current_line_number += 1

    for rule in REGEX_RULES:
        for match in rule.pattern.finditer(scanned_text):
            if rule.signal_type == "phone_number" and _phone_match_embedded_in_long_digit_run(scanned_text, match.start(), match.end()):
                continue
            if rule.signal_type == "phone_number" and not _phone_match_has_phone_context(scanned_text, match.start(), match.end()):
                continue
            if rule.signal_type == "expense_amount" and not _amount_match_has_personal_context(scanned_text, match.start(), match.end()):
                continue
            if rule.validator and not rule.validator(match.group(0)):
                continue
            snippet = f"{_display_type(rule.signal_type)}: {rule.marker}"
            _append_signal(
                signals,
                seen,
                _signal(
                    rule.signal_type,
                    rule.detector,
                    rule.confidence,
                    snippet,
                    evidence_anchor=text_position_anchor(
                        rule.signal_type,
                        rule.detector,
                        match.start(),
                        match.end(),
                        source_line_number(scanned_text, match.start()),
                        snippet,
                    ),
                ),
            )
            if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
                return signals

    return signals


def _signals_from_label_line(line: str, line_start: int, line_number: int) -> list[dict[str, Any]]:
    inline_signals = [
        signal
        for signal in (
            _signal_from_label_span(line, line_start, line_number, label, value_start, value_end)
            for label, value_start, value_end in inline_label_value_spans(line)
        )
        if signal
    ]
    if inline_signals:
        return inline_signals

    fallback = _signal_from_label_line(line, line_start, line_number)
    return [fallback] if fallback else []


def _signal_from_label_span(line: str, line_start: int, line_number: int, label: str, value_start: int, value_end: int) -> dict[str, Any] | None:
    value = line[value_start:value_end].strip()
    if not _has_filled_value(value):
        return None

    rule = rule_for_label(label, value)
    if not rule:
        return None

    snippet = f"{label}: {rule.marker}"
    return _signal(
        rule.signal_type,
        rule.detector,
        rule.confidence,
        snippet,
        evidence_anchor=text_position_anchor(
            rule.signal_type,
            rule.detector,
            line_start + value_start,
            line_start + value_end,
            line_number,
            snippet,
        ),
    )


def _signal_from_label_line(line: str, line_start: int, line_number: int) -> dict[str, Any] | None:
    match = LABEL_RE.match(line)
    if not match:
        return None

    label = _clean_label(match.group("label"))
    value = match.group("value").strip()
    if not _has_filled_value(value):
        return None

    rule = rule_for_label(label, value)
    if not rule:
        return None

    snippet = f"{label}: {rule.marker}"
    value_start, value_end = trim_span(line, match.start("value"), match.end("value"))
    return _signal(
        rule.signal_type,
        rule.detector,
        rule.confidence,
        snippet,
        evidence_anchor=text_position_anchor(
            rule.signal_type,
            rule.detector,
            line_start + value_start,
            line_start + value_end,
            line_number,
            snippet,
        ),
    )


def _overlaps_existing_signal(signal: dict[str, Any], signals: list[dict[str, Any]]) -> bool:
    span = _signal_text_span(signal)
    if not span:
        return False
    for existing in signals:
        if existing.get("type") != signal.get("type"):
            continue
        existing_span = _signal_text_span(existing)
        if existing_span and existing_span[0] < span[1] and span[0] < existing_span[1]:
            return True
    return False


def _signal_text_span(signal: dict[str, Any]) -> tuple[int, int] | None:
    anchor = signal.get("evidenceAnchor")
    if not isinstance(anchor, dict):
        return None
    selector = anchor.get("selector")
    if not isinstance(selector, dict) or selector.get("type") != "textPosition":
        return None
    start = selector.get("start")
    end = selector.get("end")
    if isinstance(start, int) and isinstance(end, int):
        return start, end
    return None


def _has_filled_value(value: str) -> bool:
    cleaned = value.strip()
    if len(cleaned) < 2:
        return False
    if PLACEHOLDER_RE.fullmatch(cleaned):
        return False
    normalized = cleaned.strip(" _.-/").lower()
    if normalized in {"n/a", "na", "none", "select", "select one", "choose one", "pending", "todo"}:
        return False
    return any(character.isalnum() for character in cleaned)


def _append_signal(signals: list[dict[str, Any]], seen: set[tuple[str, str]], signal: dict[str, Any]) -> None:
    key = (signal["type"], signal["snippet"])
    if key in seen:
        return
    if _overlaps_existing_signal(signal, signals):
        return
    if _suppressed_by_contextual_overlap(signal, signals):
        return
    seen.add(key)
    signals.append(signal)


def _suppressed_by_contextual_overlap(signal: dict[str, Any], signals: list[dict[str, Any]]) -> bool:
    blockers = WEAKER_OVERLAP_SUPPRESSIONS.get(str(signal.get("type")))
    if not blockers:
        return False
    span = _signal_text_span(signal)
    if not span:
        return False
    for existing in signals:
        if existing.get("type") not in blockers:
            continue
        existing_span = _signal_text_span(existing)
        if existing_span and existing_span[0] < span[1] and span[0] < existing_span[1]:
            return True
    return False


def _signal(signal_type: str, detector: str, confidence: float, snippet: str, *, evidence_anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    signal = {"type": signal_type, "detector": detector, "confidence": confidence, "snippet": snippet[:180], "page": None}
    if evidence_anchor:
        signal["evidenceAnchor"] = evidence_anchor
    return signal


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()


def _display_type(signal_type: str) -> str:
    return display_type(signal_type)


def _valid_ipv4(value: str) -> bool:
    return all(0 <= int(part) <= 255 for part in value.split("."))


def _valid_payment_card(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 13 or len(digits) > 19 or len(set(digits)) == 1:
        return False
    total = 0
    reverse_digits = digits[::-1]
    for index, character in enumerate(reverse_digits):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _valid_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7 or len(digits) > 15:
        return False
    if DATE_LIKE_RE.fullmatch(value.strip()):
        return False
    if SSN_RE.fullmatch(value.strip()) or _valid_payment_card(value):
        return False
    return True


def _phone_match_embedded_in_long_digit_run(text: str, start: int, end: int) -> bool:
    left = start
    right = end
    while left > 0 and text[left - 1] in "0123456789 -().+":
        left -= 1
    while right < len(text) and text[right] in "0123456789 -().+":
        right += 1
    digit_run = re.sub(r"\D", "", text[left:right])
    return len(digit_run) > 15 or _valid_payment_card(text[left:right])


def _phone_match_has_phone_context(text: str, start: int, end: int) -> bool:
    value = text[start:end]
    if "+" in value or any(character in value for character in " -()."):
        return True
    context = text[max(0, start - 32):min(len(text), end + 32)].lower()
    return any(token in context for token in (
        "phone",
        "mobile",
        "tel",
        "telephone",
        "telefon",
        "téléphone",
        "teléfono",
        "telefone",
        "telefoon",
        "電話",
        "电话",
        "전화",
        "الهاتف",
    ))


def _amount_match_has_personal_context(text: str, start: int, end: int) -> bool:
    context = text[max(0, start - 48):min(len(text), end + 48)].lower()
    return any(token in context for token in (
        "salary",
        "salaris",
        "salario",
        "gehalt",
        "compensation",
        "payroll",
        "bonus",
        "wage",
        "expense",
        "reimbursement",
        "claim",
        "allowance",
        "employee",
        "staff",
        "participant",
        "requester",
        "traveler",
    ))


def _url_has_personal_hint(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in (
        "/user/",
        "/users/",
        "/profile/",
        "/profiles/",
        "/account/",
        "/people/",
        "linkedin.com/in/",
        "github.com/",
        "x.com/",
        "twitter.com/",
    ))
