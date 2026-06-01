"""Shared risk taxonomy for redacted deterministic signal types."""

from __future__ import annotations

HIGH_RISK_SIGNAL_TYPES = frozenset({
    "bank_account",
    "biometric_data",
    "credential_secret",
    "criminal_record",
    "date_of_birth",
    "driver_license",
    "employee_id",
    "free_text_personal_context",
    "genetic_data",
    "government_identifier",
    "health_data",
    "iban_like",
    "incident_context",
    "medical_identifier",
    "national_identifier",
    "passport_number",
    "payment_card",
    "political_opinion",
    "race_ethnicity",
    "religious_belief",
    "sex_life_orientation",
    "signature",
    "tax_id",
    "trade_union",
    "travel_record",
})

MEDIUM_RISK_SIGNAL_TYPES = frozenset({
    "account_handle",
    "address",
    "email",
    "family_data",
    "license_plate",
    "location_data",
    "minor_data",
    "online_identifier",
    "organization_identifier",
    "phone_number",
    "salary_compensation",
    "student_identifier",
    "url",
    "device_identifier",
})


def public_risk_level(signal_types: set[str]) -> str:
    if signal_types & HIGH_RISK_SIGNAL_TYPES:
        return "high"
    if len(signal_types) >= 3 or signal_types & MEDIUM_RISK_SIGNAL_TYPES:
        return "medium"
    if signal_types:
        return "low"
    return "none"
