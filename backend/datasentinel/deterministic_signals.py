"""Deterministic redacted signal detection for prelaunch scans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable

MAX_SIGNAL_SCAN_CHARS = 200_000
MAX_SIGNALS_PER_DOCUMENT = 32

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b")
PHONE_RE = re.compile(r"\b(?:\+\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?){2,4}\d{2,4}\b")
EMPLOYEE_ID_RE = re.compile(r"\b(?:EMP|EE|E)-\d{3,8}\b", re.IGNORECASE)
TAX_ID_RE = re.compile(r"\b(?:[A-Z]{2}\d{8,12}|(?:tax|vat)\s*id\s*[:#]?\s*[A-Z0-9 -]{6,20})\b", re.IGNORECASE)
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
LABEL_RE = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9 /_-]{1,54})\s*[:：]\s*(?P<value>.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"^[\s._/\\|()[\]{}-]+$")
REDACTED_MARKER_RE = re.compile(r"\[REDACTED_[A-Z0-9_]+\]")
SOURCE_REFERENCE_PREFIX = "source_reference:"


@dataclass(frozen=True)
class RegexRule:
    signal_type: str
    detector: str
    marker: str
    pattern: re.Pattern[str]
    confidence: float
    validator: Callable[[str], bool] | None = None


@dataclass(frozen=True)
class LabelRule:
    signal_type: str
    detector: str
    marker: str
    confidence: float


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
LABEL_MARKERS = {rule.signal_type: rule.marker for rule in REGEX_RULES} | {
    "person_name": "[REDACTED_PERSON_NAME]",
    "date_of_birth": "[REDACTED_DATE_OF_BIRTH]",
    "address": "[REDACTED_ADDRESS]",
    "location_data": "[REDACTED_LOCATION]",
    "passport_number": "[REDACTED_PASSPORT]",
    "driver_license": "[REDACTED_DRIVER_LICENSE]",
    "license_plate": "[REDACTED_LICENSE_PLATE]",
    "bank_account": "[REDACTED_BANK_ACCOUNT]",
    "salary_compensation": "[REDACTED_COMPENSATION]",
    "student_identifier": "[REDACTED_STUDENT_ID]",
    "health_data": "[REDACTED_HEALTH_DATA]",
    "medical_identifier": "[REDACTED_MEDICAL_ID]",
    "biometric_data": "[REDACTED_BIOMETRIC_DATA]",
    "genetic_data": "[REDACTED_GENETIC_DATA]",
    "race_ethnicity": "[REDACTED_RACE_ETHNICITY]",
    "political_opinion": "[REDACTED_POLITICAL_DATA]",
    "religious_belief": "[REDACTED_BELIEF_DATA]",
    "trade_union": "[REDACTED_UNION_DATA]",
    "sex_life_orientation": "[REDACTED_SEXUAL_ORIENTATION]",
    "criminal_record": "[REDACTED_CRIMINAL_RECORD]",
    "family_data": "[REDACTED_FAMILY_DATA]",
    "minor_data": "[REDACTED_MINOR_DATA]",
    "credential_secret": "[REDACTED_SECRET]",
    "device_identifier": "[REDACTED_DEVICE_ID]",
    "online_identifier": "[REDACTED_ONLINE_ID]",
    "national_identifier": "[REDACTED_NATIONAL_ID]",
    "government_identifier": "[REDACTED_GOVERNMENT_ID]",
    "account_handle": "[REDACTED_HANDLE]",
    "url": "[REDACTED_URL]",
    "organization_identifier": "[REDACTED_ORGANIZATION]",
    "free_text_personal_context": "[REDACTED_FREE_TEXT]",
    "access_context": "[REDACTED_ACCESS_CONTEXT]",
    "incident_context": "[REDACTED_INCIDENT_CONTEXT]",
}


def detect_signals(text: str) -> list[dict[str, Any]]:
    """Return public-safe signal records without raw adjacent source context."""
    scanned_text = text[:MAX_SIGNAL_SCAN_CHARS]
    signals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for line in scanned_text.splitlines():
        label_signal = _signal_from_label_line(line)
        if label_signal:
            _append_signal(signals, seen, label_signal)
            if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
                return signals

    for rule in REGEX_RULES:
        for match in rule.pattern.finditer(scanned_text):
            if rule.signal_type == "phone_number" and _phone_match_embedded_in_long_digit_run(scanned_text, match.start(), match.end()):
                continue
            if rule.validator and not rule.validator(match.group(0)):
                continue
            _append_signal(signals, seen, _signal(rule.signal_type, rule.detector, rule.confidence, f"{_display_type(rule.signal_type)}: {rule.marker}"))
            if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
                return signals

    return signals


def safe_public_source_path(source_path: str) -> str:
    if source_path.startswith(SOURCE_REFERENCE_PREFIX):
        return source_path
    if _is_unsafe_source_path(source_path):
        return f"{SOURCE_REFERENCE_PREFIX}{sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
    return source_path


def sanitize_public_signal(signal: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(signal)
    signal_type = str(sanitized.get("type") or "value")
    snippet = str(sanitized.get("snippet") or "")
    marker = _redacted_marker(snippet, signal_type)
    sanitized["snippet"] = f"{_display_type(signal_type)}: {marker}"[:180]
    return sanitized


def _signal_from_label_line(line: str) -> dict[str, Any] | None:
    match = LABEL_RE.match(line)
    if not match:
        return None

    label = _clean_label(match.group("label"))
    value = match.group("value").strip()
    if not _has_filled_value(value):
        return None

    rule = _rule_for_label(label, value)
    if not rule:
        return None

    return _signal(rule.signal_type, rule.detector, rule.confidence, f"{label}: {rule.marker}")


def _rule_for_label(label: str, value: str) -> LabelRule | None:
    normalized = _normalize_label(label)
    lowered_value = value.lower()

    if "email" in normalized:
        return LabelRule("email", "email_label", "[REDACTED_EMAIL]", 0.86)
    if "phone" in normalized or "mobile" in normalized:
        return LabelRule("phone_number", "phone_label", "[REDACTED_PHONE]", 0.84)
    if any(token in normalized for token in ("date of birth", "birth date", "dob", "born")):
        return LabelRule("date_of_birth", "date_of_birth_label", "[REDACTED_DATE_OF_BIRTH]", 0.86)
    if "tax" in normalized or "vat" in normalized:
        return LabelRule("tax_id", "tax_id_label", "[REDACTED_TAX_ID]", 0.84)
    if any(token in normalized for token in ("passport", "passport number")):
        return LabelRule("passport_number", "passport_label", "[REDACTED_PASSPORT]", 0.87)
    if any(token in normalized for token in ("driver license", "driving licence", "drivers license", "license number", "licence number")):
        return LabelRule("driver_license", "driver_license_label", "[REDACTED_DRIVER_LICENSE]", 0.84)
    if any(token in normalized for token in ("national id", "identity number", "identification number", "ssn", "social security", "nino")):
        return LabelRule("national_identifier", "national_identifier_label", "[REDACTED_NATIONAL_ID]", 0.86)
    if any(token in normalized for token in ("government id", "resident permit", "visa number", "citizen id")):
        return LabelRule("government_identifier", "government_identifier_label", "[REDACTED_GOVERNMENT_ID]", 0.82)
    if any(token in normalized for token in ("student id", "student number", "learner id")):
        return LabelRule("student_identifier", "student_identifier_label", "[REDACTED_STUDENT_ID]", 0.82)
    if any(token in normalized for token in ("medical record", "patient id", "health insurance", "insurance id", "nhs number")):
        return LabelRule("medical_identifier", "medical_identifier_label", "[REDACTED_MEDICAL_ID]", 0.86)
    if any(token in normalized for token in ("employee id", "staff id", "personnel number", "worker id")) or EMPLOYEE_ID_RE.search(value):
        return LabelRule("employee_id", "employee_id_label", "[REDACTED_EMPLOYEE_ID]", 0.85)
    if any(token in normalized for token in ("credit card", "card number", "payment card")):
        return LabelRule("payment_card", "payment_card_label", "[REDACTED_PAYMENT_CARD]", 0.86)
    if any(token in normalized for token in ("bank account", "account number", "routing number", "sort code", "bic", "swift")):
        return LabelRule("bank_account", "bank_account_label", "[REDACTED_BANK_ACCOUNT]", 0.84)
    if "iban" in normalized:
        return LabelRule("iban_like", "iban_label", "[REDACTED_FINANCIAL_ID]", 0.88)
    if any(token in normalized for token in ("salary", "compensation", "payroll", "bonus", "wage")):
        return LabelRule("salary_compensation", "compensation_label", "[REDACTED_COMPENSATION]", 0.8)
    if any(token in normalized for token in ("amount", "expense", "reimbursement")) or AMOUNT_RE.search(value):
        return LabelRule("expense_amount", "amount_label", "[REDACTED_AMOUNT]", 0.82)
    if any(token in normalized for token in ("ip address", "ipv4", "ipv6", "online identifier", "cookie id", "advertising id", "tracking id")):
        return LabelRule("online_identifier", "online_identifier_label", "[REDACTED_ONLINE_ID]", 0.78)
    if any(token in normalized for token in ("device id", "imei", "serial number", "mac address", "hardware id")):
        return LabelRule("device_identifier", "device_identifier_label", "[REDACTED_DEVICE_ID]", 0.8)
    if any(token in normalized for token in ("address", "street address", "home address", "postal address")):
        return LabelRule("address", "address_label", "[REDACTED_ADDRESS]", 0.79)
    if any(token in normalized for token in ("location", "gps", "latitude", "longitude", "geo", "geolocation")):
        return LabelRule("location_data", "location_label", "[REDACTED_LOCATION]", 0.8)
    if any(token in normalized for token in ("license plate", "licence plate", "registration plate", "vehicle registration", "plate number")):
        return LabelRule("license_plate", "license_plate_label", "[REDACTED_LICENSE_PLATE]", 0.78)
    if any(token in normalized for token in ("username", "user name", "handle", "account id", "profile id", "login id")):
        return LabelRule("account_handle", "account_handle_label", "[REDACTED_HANDLE]", 0.76)
    if any(token in normalized for token in ("profile url", "personal url", "social link", "account url")):
        return LabelRule("url", "url_label", "[REDACTED_URL]", 0.72)
    if any(token in normalized for token in ("password", "passcode", "api key", "secret", "token", "session id", "cookie")):
        return LabelRule("credential_secret", "credential_secret_label", "[REDACTED_SECRET]", 0.76)
    if any(token in normalized for token in ("diagnosis", "medical condition", "medication", "allergy", "disability", "sick leave", "health status", "doctor", "patient")):
        return LabelRule("health_data", "health_data_label", "[REDACTED_HEALTH_DATA]", 0.82)
    if any(token in normalized for token in ("fingerprint", "face id", "facial recognition", "voiceprint", "iris", "retina", "biometric")):
        return LabelRule("biometric_data", "biometric_data_label", "[REDACTED_BIOMETRIC_DATA]", 0.84)
    if any(token in normalized for token in ("dna", "genetic", "genome")):
        return LabelRule("genetic_data", "genetic_data_label", "[REDACTED_GENETIC_DATA]", 0.84)
    if any(token in normalized for token in ("race", "racial", "ethnicity", "ethnic origin")):
        return LabelRule("race_ethnicity", "race_ethnicity_label", "[REDACTED_RACE_ETHNICITY]", 0.8)
    if any(token in normalized for token in ("political", "party membership", "political opinion")):
        return LabelRule("political_opinion", "political_opinion_label", "[REDACTED_POLITICAL_DATA]", 0.8)
    if any(token in normalized for token in ("religion", "religious", "belief", "philosophical")):
        return LabelRule("religious_belief", "religious_belief_label", "[REDACTED_BELIEF_DATA]", 0.8)
    if any(token in normalized for token in ("trade union", "union membership")):
        return LabelRule("trade_union", "trade_union_label", "[REDACTED_UNION_DATA]", 0.8)
    if any(token in normalized for token in ("sexual orientation", "sex life")):
        return LabelRule("sex_life_orientation", "sex_life_orientation_label", "[REDACTED_SEXUAL_ORIENTATION]", 0.8)
    if any(token in normalized for token in ("criminal", "conviction", "offence", "offense", "background check")):
        return LabelRule("criminal_record", "criminal_record_label", "[REDACTED_CRIMINAL_RECORD]", 0.8)
    if any(token in normalized for token in ("child", "minor", "guardian", "parent name")):
        return LabelRule("minor_data", "minor_data_label", "[REDACTED_MINOR_DATA]", 0.76)
    if any(token in normalized for token in ("spouse", "dependent", "emergency contact", "next of kin", "family")):
        return LabelRule("family_data", "family_data_label", "[REDACTED_FAMILY_DATA]", 0.76)
    if any(token in normalized for token in ("access", "system", "department", "role", "justification")):
        return LabelRule("access_context", "access_context_label", "[REDACTED_ACCESS_CONTEXT]", 0.76)
    if any(token in normalized for token in ("incident", "description", "root cause", "corrective action", "deadline", "location", "impact")):
        return LabelRule("incident_context", "incident_context_label", "[REDACTED_INCIDENT_CONTEXT]", 0.76)
    if any(token in normalized for token in ("comment", "recommendation", "feedback", "evaluation")):
        return LabelRule("free_text_personal_context", "free_text_context_label", "[REDACTED_FREE_TEXT]", 0.74)
    if _looks_like_person_label(normalized) and not any(token in lowered_value for token in ("ltd", "llc", "gmbh", "inc", "limited")):
        return LabelRule("person_name", "person_label", "[REDACTED_PERSON_NAME]", 0.78)
    if "company" in normalized or "supplier" in normalized:
        return LabelRule("organization_identifier", "organization_label", "[REDACTED_ORGANIZATION]", 0.7)
    return None


def _looks_like_person_label(normalized: str) -> bool:
    return any(token in normalized for token in (
        "name",
        "employee",
        "participant",
        "manager",
        "approver",
        "reviewer",
        "owner",
        "requester",
        "reported by",
        "signature",
        "contact person",
        "trainer",
    ))


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


def _is_unsafe_source_path(source_path: str) -> bool:
    lowered = source_path.lower()
    return (
        "://" in source_path
        or lowered.startswith("www.")
        or source_path.startswith("/")
        or source_path.startswith("~/")
        or bool(re.match(r"^[A-Za-z]:[\\/]", source_path))
    )


def _redacted_marker(snippet: str, signal_type: str) -> str:
    marker = REDACTED_MARKER_RE.search(snippet)
    if marker:
        return marker.group(0)
    return LABEL_MARKERS.get(signal_type, "[REDACTED_VALUE]")


def _append_signal(signals: list[dict[str, Any]], seen: set[tuple[str, str]], signal: dict[str, Any]) -> None:
    key = (signal["type"], signal["snippet"])
    if key in seen:
        return
    seen.add(key)
    signals.append(signal)


def _signal(signal_type: str, detector: str, confidence: float, snippet: str) -> dict[str, Any]:
    return {"type": signal_type, "detector": detector, "confidence": confidence, "snippet": snippet[:180], "page": None}


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()


def _normalize_label(label: str) -> str:
    return _clean_label(label).lower()


def _display_type(signal_type: str) -> str:
    return signal_type.replace("_", " ").title()


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
