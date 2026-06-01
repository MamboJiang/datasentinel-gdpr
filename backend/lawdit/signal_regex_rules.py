"""Regex-based deterministic signal rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from .signal_evidence_anchors import display_type, line_number as source_line_number, text_position_anchor

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


def regex_signals(text: str) -> Iterator[dict[str, Any]]:
    for rule in REGEX_RULES:
        for match in rule.pattern.finditer(text):
            if rule.signal_type == "phone_number" and _phone_match_embedded_in_long_digit_run(text, match.start(), match.end()):
                continue
            if rule.signal_type == "phone_number" and not _phone_match_has_phone_context(text, match.start(), match.end()):
                continue
            if rule.signal_type == "expense_amount" and not _amount_match_has_personal_context(text, match.start(), match.end()):
                continue
            if rule.validator and not rule.validator(match.group(0)):
                continue
            snippet = f"{display_type(rule.signal_type)}: {rule.marker}"
            yield {
                "type": rule.signal_type,
                "detector": rule.detector,
                "confidence": rule.confidence,
                "snippet": snippet[:180],
                "page": None,
                "evidenceAnchor": text_position_anchor(
                    rule.signal_type,
                    rule.detector,
                    match.start(),
                    match.end(),
                    source_line_number(text, match.start()),
                    snippet,
                ),
            }


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
