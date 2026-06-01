"""Build redacted public analysis results for the website entry."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from .deterministic_signals import detect_signals
from .public_analysis_plain_language import plain_language_summary
from .signal_evidence_anchors import apply_source_locations, sanitize_public_signal
from .signal_risk import public_risk_level
from .source_format_recognition import extract_document_content

_PUBLIC_SELECTOR_KEYS = (
    "type",
    "start",
    "end",
    "sourceStart",
    "sourceEnd",
    "page",
    "row",
    "column",
    "columnLabel",
    "path",
    "partName",
    "paragraphIndex",
    "slideNumber",
    "shapeIndex",
    "tagName",
    "nodeIndex",
    "recordIndex",
    "lineNumber",
    "columnNumber",
    "fieldIndex",
    "elementIndex",
    "attributeIndex",
    "blockLabel",
    "frameIndex",
)
_PUBLIC_SELECTOR_STRING_KEYS = {"type", "columnLabel", "path", "partName", "tagName", "blockLabel"}
_PUBLIC_PAGE_REGION_KEYS = ("x", "y", "width", "height", "pageWidth", "pageHeight", "unit", "origin", "confidence", "ocrConfidence")
_PUBLIC_SAFE_STRING_RE = re.compile(r"^[A-Za-z0-9_./:#\[\] -]{1,120}$")
_PUBLIC_SAFE_LABEL_RE = re.compile(
    r"^(?:Line \d+|Page \d+|Image OCR text|Frame \d+ OCR text|Transcript text|"
    r"DOCX paragraph \d+|ODT paragraph \d+|Slide \d+ shape \d+|HTML [a-z0-9]+ \d+|"
    r"XML element [0-9.]+(?: attribute \d+)?|(?:JSON|JSONL|NDJSON)(?: record \d+)? field [0-9.]+|"
    r"Email (?:header|body part) \d+|ZIP member \d+(?:: [A-Za-z0-9_./:#\[\] -]{1,80})?|"
    r"row \d+ column [A-Z]+)$"
)


def analyze_public_upload(*, name: str, content_type: str, body: bytes) -> dict[str, Any]:
    extracted = extract_document_content(body=body, content_type=content_type, name=name)
    signals = [
        sanitize_public_signal(signal)
        for signal in apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
    ]
    detected_types = _detected_types(signals)
    risk_level = public_risk_level({str(item["type"]) for item in detected_types})
    evidence = [_public_evidence(signal) for signal in signals[:5]]

    return {
        "analysisId": _analysis_id(name, body),
        "status": "completed",
        "file": {
            "name": name,
            "sizeBytes": len(body),
            "fileFormat": extracted.file_format,
            "extractionMethod": extracted.extraction_method,
            "recognitionDifficulty": extracted.recognition_difficulty,
        },
        "summary": {
            "detectedSignalCount": len(signals),
            "detectedTypes": detected_types,
            "riskLevel": risk_level,
            "plainLanguageSummary": plain_language_summary(
                detected_types=detected_types,
                evidence_locations=_evidence_locations(evidence),
                file_format=extracted.file_format,
                recognition_difficulty=extracted.recognition_difficulty,
                risk_level=risk_level,
                signal_count=len(signals),
            ),
            "reviewRecommendation": _review_recommendation(risk_level, len(signals)),
            "nextSteps": _next_steps(risk_level, len(signals)),
            "workflowReadiness": _workflow_readiness(extracted.recognition_difficulty, len(signals)),
            "boundaryNotes": _boundary_notes(),
            "rawContentExposed": False,
            "legalConclusionProvided": False,
            "deletionAvailable": False,
        },
        "analysisStages": _analysis_stages(
            extracted.file_format,
            extracted.extraction_method,
            extracted.recognition_difficulty,
            len(signals),
            risk_level,
        ),
        "governanceBoundaries": _governance_boundaries(),
        "evidence": evidence,
        "warnings": _result_warnings(extracted.recognition_difficulty, len(signals)),
    }


def _detected_types(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        signal_type = str(signal.get("type") or "unknown")
        current = grouped.setdefault(signal_type, {"type": signal_type, "count": 0, "highestConfidence": 0.0})
        current["count"] += 1
        confidence = signal.get("confidence")
        if isinstance(confidence, (int, float)):
            current["highestConfidence"] = max(float(current["highestConfidence"]), round(float(confidence), 2))
    return sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["type"])))


def _evidence_locations(evidence: list[dict[str, Any]]) -> list[str]:
    locations: list[str] = []
    for item in evidence:
        label = _safe_public_label(item.get("locationLabel"))
        if label != "Detected text" and label not in locations:
            locations.append(label)
    return locations


def _review_recommendation(risk_level: str, signal_count: int) -> str:
    if signal_count == 0:
        return "No GDPR-relevant deterministic signal was detected. Review the source context manually before relying on this result."
    if risk_level == "high":
        return "Treat this as a priority review candidate and verify the redacted evidence in a governed Workspace before deciding next actions."
    if risk_level == "medium":
        return "Review the file with an accountable owner because multiple or moderate-confidence data signals were detected."
    return "Review the matched evidence before deciding whether the file needs governed follow-up."


def _next_steps(risk_level: str, signal_count: int) -> list[str]:
    if signal_count == 0:
        return [
            "Confirm the file context with the team that owns the source.",
            "Use a governed Workspace scan when the source needs audit history or repeated monitoring.",
        ]
    if risk_level == "high":
        return [
            "Verify each redacted evidence snippet with an accountable reviewer.",
            "Route the case to the file owner or DPO escalation path before deciding retention or cleanup.",
            "Open the Workspace when owner assignment, audit history, or evaluation tracking is needed.",
        ]
    if risk_level == "medium":
        return [
            "Assign an accountable owner to confirm whether the detected signals are expected.",
            "Record a human decision in the Workspace before any cleanup planning.",
        ]
    return [
        "Review the matched evidence with the source owner.",
        "Move to the Workspace if the file belongs in a governed source inventory.",
    ]


def _workflow_readiness(recognition_difficulty: str, signal_count: int) -> list[str]:
    readiness = ["Redacted evidence is ready for human review.", "Raw source content is not returned in the public response."]
    if signal_count:
        readiness.append("Detected signal categories can be handed to owner routing in the Workspace.")
    else:
        readiness.append("Manual source-context review is still required when no deterministic signal is detected.")
    if recognition_difficulty in {"hard", "unsupported"}:
        readiness.append("Extraction difficulty should be reviewed before relying on the result.")
    return readiness


def _boundary_notes() -> list[str]:
    return [
        "No Workspace source, finding, audit event, or deletion action is created from this upload.",
        "The response is not legal advice and does not claim GDPR compliance.",
    ]


def _analysis_stages(
    file_format: str,
    extraction_method: str,
    recognition_difficulty: str,
    signal_count: int,
    risk_level: str,
) -> list[dict[str, str]]:
    return [
        {"name": "File intake", "status": "completed", "description": f"{file_format or 'file'} input accepted inside the one-file, 10 MB boundary."},
        {
            "name": "Readable content extraction",
            "status": "completed" if recognition_difficulty != "unsupported" else "limited",
            "description": f"Content was handled through {extraction_method or 'the configured extractor'} with {recognition_difficulty or 'unknown'} recognition difficulty.",
        },
        {
            "name": "Signal detection",
            "status": "completed",
            "description": f"{signal_count} redacted signal candidate{'s' if signal_count != 1 else ''} produced a {risk_level} review priority.",
        },
        {
            "name": "Workspace handoff",
            "status": "ready",
            "description": "Use the governed Workspace when this file needs owner routing, audit history, or evaluation tracking.",
        },
    ]


def _governance_boundaries() -> list[str]:
    return [
        "One uploaded file per browser session at a time.",
        "Ten active public analyses across the API process.",
        "No automatic deletion, raw-content exposure, legal conclusion, or tenant integration.",
    ]


def _public_evidence(signal: dict[str, Any]) -> dict[str, Any]:
    anchor = signal.get("evidenceAnchor") if isinstance(signal.get("evidenceAnchor"), dict) else {}
    fallback = anchor.get("fallback") if isinstance(anchor.get("fallback"), dict) else {}
    location = _public_evidence_location(anchor)
    evidence = {
        "type": signal.get("type") or "unknown",
        "detector": signal.get("detector") or "unknown",
        "confidence": round(float(signal.get("confidence") or 0), 2),
        "snippet": str(signal.get("snippet") or "[REDACTED_VALUE]")[:180],
        "locationLabel": location["label"] if location else _safe_public_label(fallback.get("label") or anchor.get("label")),
    }
    if location:
        evidence["location"] = location
    return evidence


def _public_evidence_location(anchor: dict[str, Any]) -> dict[str, Any] | None:
    if not anchor:
        return None
    fallback = anchor.get("fallback") if isinstance(anchor.get("fallback"), dict) else {}
    selector = anchor.get("selector") if isinstance(anchor.get("selector"), dict) else None
    safe_selector = _safe_public_selector(selector) if selector else None
    location: dict[str, Any] = {
        "format": _safe_public_string(anchor.get("format")) or "unknown",
        "label": _public_location_label(anchor, fallback, safe_selector),
        "rawContentExposed": False,
    }
    anchor_id = _safe_public_string(anchor.get("anchorId"))
    if anchor_id:
        location["anchorId"] = anchor_id
    if safe_selector:
        location["selector"] = safe_selector
    return location


def _safe_public_selector(selector: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in _PUBLIC_SELECTOR_KEYS:
        if key not in selector:
            continue
        value = selector[key]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            safe[key] = value
        elif key == "blockLabel":
            safe_value = _safe_public_label(value)
            if safe_value != "Detected text":
                safe[key] = safe_value
        elif key in _PUBLIC_SELECTOR_STRING_KEYS:
            safe_value = _safe_public_string(value)
            if safe_value:
                safe[key] = safe_value
    region = selector.get("pageRegion")
    if isinstance(region, dict):
        safe_region: dict[str, Any] = {}
        for key in _PUBLIC_PAGE_REGION_KEYS:
            value = region.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                safe_region[key] = value
            else:
                safe_value = _safe_public_string(value)
                if safe_value:
                    safe_region[key] = safe_value
        if safe_region:
            safe["pageRegion"] = safe_region
    return safe


def _public_location_label(anchor: dict[str, Any], fallback: dict[str, Any], selector: dict[str, Any] | None) -> str:
    if selector:
        selector_type = selector.get("type")
        if selector_type == "tableCell":
            return _table_cell_label(selector)
        if selector_type == "textPosition":
            page = selector.get("page")
            line = selector.get("lineNumber")
            if isinstance(page, int):
                return f"Page {page}"
            if isinstance(line, int):
                return f"Line {line}"
        block_label = _safe_public_label(selector.get("blockLabel"))
        if block_label != "Detected text":
            return block_label
    return _safe_public_label(fallback.get("label") or anchor.get("label"))


def _table_cell_label(selector: dict[str, Any]) -> str:
    row = selector.get("row")
    column_label = selector.get("columnLabel")
    if isinstance(row, int) and isinstance(column_label, str):
        return f"row {row} column {column_label}"
    return "Table cell"


def _safe_public_label(value: Any) -> str:
    label = str(value or "").strip()
    if label and _PUBLIC_SAFE_LABEL_RE.fullmatch(label):
        return label
    return "Detected text"


def _safe_public_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or not _PUBLIC_SAFE_STRING_RE.fullmatch(normalized):
        return None
    return normalized


def _result_warnings(recognition_difficulty: str, signal_count: int) -> list[str]:
    warnings: list[str] = []
    if recognition_difficulty in {"hard", "unsupported"}:
        warnings.append("Extraction required a hard recognition path; review coverage before relying on the result.")
    if signal_count == 0:
        warnings.append("No deterministic signal match is not proof that the file contains no personal data.")
    return warnings


def _analysis_id(name: str, body: bytes) -> str:
    digest = hashlib.sha256(name.encode("utf-8") + body[:65_536]).hexdigest()[:12]
    return f"analysis_{int(time.time() * 1000)}_{digest}"
