"""Plain-language public analysis summaries derived from redacted results."""

from __future__ import annotations

from typing import Any

_SIGNAL_COPY = {
    "address": ("address", "can identify or locate a person"),
    "bank_account": ("bank account", "can identify a person in a financial context"),
    "biometric_data": ("biometric data", "can indicate a special-category biometric context"),
    "credential_secret": ("credential secret", "can create access or account-takeover risk if exposed"),
    "date_of_birth": ("date of birth", "can identify a person when combined with other details"),
    "driver_license": ("driver licence number", "can directly identify a person through an official document"),
    "email": ("email address", "can identify or contact a person"),
    "employee_id": ("employee identifier", "can identify a worker inside an organisation"),
    "government_identifier": ("government identifier", "can directly identify a person through an official identifier"),
    "health_data": ("health data", "can indicate a special-category health context"),
    "iban_like": ("IBAN-like bank identifier", "can identify a person or account in a financial context"),
    "license_plate": ("licence plate", "can identify a vehicle linked to a person"),
    "location_data": ("location data", "can reveal where a person is or has been"),
    "medical_identifier": ("medical identifier", "can identify a person in a healthcare context"),
    "minor_data": ("minor-related data", "can indicate data about a child or young person"),
    "national_identifier": ("national identifier", "can directly identify a person through a state or employment identifier"),
    "online_identifier": ("online identifier", "can identify a person or browser over time"),
    "passport_number": ("passport number", "can directly identify a person through an official travel document"),
    "payment_card": ("payment card number", "can identify a person in a payment context"),
    "person_name": ("person name", "can identify a person when combined with file context"),
    "phone_number": ("phone number", "can identify or contact a person"),
    "political_opinion": ("political opinion indicator", "can indicate a special-category political-opinion context"),
    "race_ethnicity": ("race or ethnicity indicator", "can indicate a special-category race or ethnicity context"),
    "religious_belief": ("religious belief indicator", "can indicate a special-category religious-belief context"),
    "salary_compensation": ("salary or compensation detail", "can reveal employment or compensation information about a person"),
    "sex_life_orientation": ("sex life or orientation indicator", "can indicate a special-category sex life or orientation context"),
    "signature": ("signature", "can authenticate or identify a person"),
    "student_identifier": ("student identifier", "can identify a learner inside an education context"),
    "tax_id": ("tax identifier", "can directly identify a person in a tax or payroll context"),
    "trade_union": ("trade union indicator", "can indicate a special-category trade-union context"),
    "travel_record": ("travel record", "can reveal a person's movement or travel history"),
    "url": ("URL", "can point to an online profile, account, or resource linked to a person"),
}


def plain_language_summary(
    *,
    detected_types: list[dict[str, Any]],
    evidence_locations: list[str],
    file_format: str,
    recognition_difficulty: str,
    risk_level: str,
    signal_count: int,
) -> dict[str, Any]:
    format_label = _format_label(file_format)
    if signal_count == 0:
        return {
            "headline": f"lawdit did not find a deterministic GDPR-relevant signal in this {format_label} file.",
            "explanation": "The readable content did not match the configured patterns for identifiers, contact details, credentials, financial data, or special-category indicators.",
            "gdprRelevance": "This is not proof that the file is free of personal data; file purpose, source context, and unsupported content still need owner review.",
            "reviewFocus": _no_signal_review_focus(recognition_difficulty),
            "detectedCategoryLabels": [],
            "evidenceLocations": [],
        }

    counted_categories = [_counted_signal_label(item) for item in detected_types]
    return {
        "headline": f"This {format_label} file contains {_join_human_list(counted_categories)}.",
        "explanation": _plain_explanation(risk_level, signal_count),
        "gdprRelevance": f"GDPR relevance: {_join_human_list(_relevance_notes(detected_types))}.",
        "reviewFocus": _review_focus(risk_level, evidence_locations),
        "detectedCategoryLabels": [_signal_label(str(item.get("type") or "unknown")).title() for item in detected_types],
        "evidenceLocations": evidence_locations,
    }


def _plain_explanation(risk_level: str, signal_count: int) -> str:
    plural = "s" if signal_count != 1 else ""
    if risk_level == "high":
        return f"lawdit found {signal_count} redacted signal candidate{plural}, including at least one category that should be treated as priority personal-data evidence before retention, sharing, or cleanup decisions."
    if risk_level == "medium":
        return f"lawdit found {signal_count} redacted signal candidate{plural} that can identify, contact, or profile a person and should be checked by an accountable owner."
    return f"lawdit found {signal_count} redacted signal candidate{plural}. The match still needs context before deciding whether the file belongs in a governed source inventory."


def _review_focus(risk_level: str, locations: list[str]) -> str:
    location_note = f"Start with {_join_human_list(locations[:3])}." if locations else "Start with the redacted evidence rows below."
    if risk_level == "high":
        return f"{location_note} Confirm the file owner and route the review before making any retention, sharing, or cleanup decision."
    if risk_level == "medium":
        return f"{location_note} Ask the source owner whether these signals are expected for this file."
    return f"{location_note} Confirm the business context before relying on the result."


def _no_signal_review_focus(recognition_difficulty: str) -> str:
    if recognition_difficulty in {"hard", "unsupported"}:
        return "Because extraction was difficult, confirm whether hidden, scanned, or unsupported content needs a governed Workspace review."
    return "Confirm the file purpose and source owner before relying on a no-signal result."


def _relevance_notes(detected_types: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for item in detected_types[:3]:
        signal_type = str(item.get("type") or "unknown")
        label, relevance = _signal_copy(signal_type)
        notes.append(f"{label} {relevance}")
    remaining = len(detected_types) - len(notes)
    if remaining > 0:
        notes.append(f"{remaining} other categor{'y' if remaining == 1 else 'ies'} also needs accountable review")
    return notes


def _counted_signal_label(item: dict[str, Any]) -> str:
    count = int(item.get("count") or 0)
    noun = "signal" if count == 1 else "signals"
    return f"{count} {_signal_label(str(item.get('type') or 'unknown'))} {noun}"


def _signal_copy(signal_type: str) -> tuple[str, str]:
    return _SIGNAL_COPY.get(signal_type, (_signal_label(signal_type), "may relate to an identifiable person"))


def _signal_label(signal_type: str) -> str:
    return _SIGNAL_COPY.get(signal_type, (signal_type.replace("_", " "), ""))[0]


def _format_label(file_format: str) -> str:
    normalized = (file_format or "uploaded").replace("_", " ").strip()
    return normalized or "uploaded"


def _join_human_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
