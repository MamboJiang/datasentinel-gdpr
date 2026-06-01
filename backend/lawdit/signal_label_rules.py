"""Label-to-signal rules for deterministic scanner output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .signal_multilingual_labels import match_multilingual_label

EMPLOYEE_ID_VALUE_RE = re.compile(r"\b(?:EMP|EE|E)-\d{3,8}\b", re.IGNORECASE)
AMOUNT_VALUE_RE = re.compile(r"\b(?:EUR|USD|GBP|CHF)\s?\d{1,6}(?:[,.]\d{2})?\b|\b\d{1,6}(?:[,.]\d{2})\s?(?:EUR|USD|GBP|CHF)\b")
PASSPORT_VALUE_RE = re.compile(r"\b(?=[A-Z0-9]{6,15}\b)(?=[A-Z0-9]*\d)[A-Z]{1,3}[A-Z0-9]{5,12}\b", re.IGNORECASE)


@dataclass(frozen=True)
class LabelRule:
    signal_type: str
    detector: str
    marker: str
    confidence: float


def rule_for_label(label: str, value: str) -> LabelRule | None:
    normalized = _normalize_label(label)
    lowered_value = value.lower()
    multilingual_rule = match_multilingual_label(label)
    if multilingual_rule:
        return LabelRule(multilingual_rule.signal_type, multilingual_rule.detector, multilingual_rule.marker, multilingual_rule.confidence)

    if "email" in normalized:
        return LabelRule("email", "email_label", "[REDACTED_EMAIL]", 0.86)
    if "phone" in normalized or "mobile" in normalized:
        return LabelRule("phone_number", "phone_label", "[REDACTED_PHONE]", 0.84)
    if any(token in normalized for token in ("date of birth", "birth date", "dob", "born")):
        return LabelRule("date_of_birth", "date_of_birth_label", "[REDACTED_DATE_OF_BIRTH]", 0.86)
    if "tax" in normalized or "vat" in normalized:
        return LabelRule("tax_id", "tax_id_label", "[REDACTED_TAX_ID]", 0.84)
    if any(token in normalized for token in ("passport", "passport number")):
        if not PASSPORT_VALUE_RE.search(value):
            return None
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
    if any(token in normalized for token in ("employee id", "staff id", "personnel number", "worker id")) or EMPLOYEE_ID_VALUE_RE.search(value):
        return LabelRule("employee_id", "employee_id_label", "[REDACTED_EMPLOYEE_ID]", 0.85)
    if any(token in normalized for token in ("credit card", "card number", "payment card")):
        return LabelRule("payment_card", "payment_card_label", "[REDACTED_PAYMENT_CARD]", 0.86)
    if any(token in normalized for token in ("bank account", "account number", "routing number", "sort code", "bic", "swift")):
        return LabelRule("bank_account", "bank_account_label", "[REDACTED_BANK_ACCOUNT]", 0.84)
    if "iban" in normalized:
        return LabelRule("iban_like", "iban_label", "[REDACTED_FINANCIAL_ID]", 0.88)
    if any(token in normalized for token in ("salary", "compensation", "payroll", "bonus", "wage")):
        return LabelRule("salary_compensation", "compensation_label", "[REDACTED_COMPENSATION]", 0.8)
    if any(token in normalized for token in ("expense", "reimbursement", "receipt", "claim", "allowance")):
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


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()


def _normalize_label(label: str) -> str:
    return _clean_label(label).lower()


def _looks_like_person_label(normalized: str) -> bool:
    if any(token in normalized for token in ("team", "department", "group", "workstream", "queue", "service")):
        return False
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
