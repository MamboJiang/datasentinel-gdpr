"""Public single-file analysis boundary for the website entry."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
from pathlib import Path, PurePath
from typing import Any

from .deterministic_signals import detect_signals
from .envelope import envelope, problem, response
from .public_analysis_capacity import MAX_UPLOAD_BYTES, PublicAnalysisCapacity
from .signal_evidence_anchors import apply_source_locations, sanitize_public_signal
from .signal_risk import public_risk_level
from .source_archive_text import ARCHIVE_CONTENT_TYPES
from .source_format_recognition import (
    EMAIL_CONTENT_TYPES,
    OFFICE_CONTENT_TYPES,
    OPENDOCUMENT_CONTENT_TYPES,
    PDF_CONTENT_TYPES,
    SNIFFABLE_TEXT_CONTENT_TYPES,
    SUPPORTED_SUFFIXES,
    DocumentExtractionIssue,
    extract_document_content,
)
from .source_legacy_office import LEGACY_OFFICE_CONTENT_TYPES
from .source_media_recognition import IMAGE_CONTENT_TYPES, VIDEO_TRANSCRIPT_CONTENT_TYPES

MAX_MULTIPART_OVERHEAD_BYTES = 256 * 1024
MAX_MULTIPART_REQUEST_BYTES = MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES
TRIAL_SESSION_HEADER = "X-Lawdit-Trial-Session"

_SAFE_SESSION_RE = re.compile(r"[^A-Za-z0-9_.:-]")
_PUBLIC_TEXT_CONTENT_TYPES = {
    "application/json",
    "application/rtf",
    "application/xml",
    "application/x-ndjson",
    "message/rfc822",
    "text/csv",
    "text/html",
    "text/markdown",
    "text/plain",
    "text/tab-separated-values",
    "text/xml",
}
_PUBLIC_DOCUMENT_CONTENT_TYPES = (
    _PUBLIC_TEXT_CONTENT_TYPES
    | PDF_CONTENT_TYPES
    | EMAIL_CONTENT_TYPES
    | OFFICE_CONTENT_TYPES
    | LEGACY_OFFICE_CONTENT_TYPES
    | OPENDOCUMENT_CONTENT_TYPES
    | ARCHIVE_CONTENT_TYPES
    | IMAGE_CONTENT_TYPES
    | VIDEO_TRANSCRIPT_CONTENT_TYPES
)

@dataclass(frozen=True)
class UploadFile:
    name: str
    content_type: str
    body: bytes


class PublicAnalysisService:
    def __init__(self, capacity: PublicAnalysisCapacity | None = None) -> None:
        self.capacity = capacity or PublicAnalysisCapacity()

    def capacity_response(self, headers: dict[str, str], trace_id: str) -> dict[str, Any]:
        session_id = session_id_from_headers(headers)
        return response(200, envelope(self.capacity.status(session_id), trace_id), trace_id)

    def analyze_response(
        self,
        *,
        body: str | bytes | None,
        content_type: str | None,
        headers: dict[str, str],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        if not content_type or "multipart/form-data" not in content_type.lower():
            return _problem_response(
                415,
                "Unsupported media type",
                "Public analysis upload requires multipart/form-data with one file field.",
                path,
                trace_id,
                "unsupported-media-type",
            )

        raw_body = body.encode("utf-8") if isinstance(body, str) else (body or b"")
        if len(raw_body) > MAX_MULTIPART_REQUEST_BYTES:
            return _too_large_response(path, trace_id, self.capacity.status(session_id_from_headers(headers)))

        upload = _parse_upload(raw_body, content_type)
        if isinstance(upload, dict):
            return _problem_response(
                upload["status"],
                upload["title"],
                upload["detail"],
                path,
                trace_id,
                upload["code"],
            )

        if len(upload.body) > MAX_UPLOAD_BYTES:
            return _too_large_response(path, trace_id, self.capacity.status(session_id_from_headers(headers)))
        if not upload.body:
            return _problem_response(422, "Request validation failed", "Uploaded file must not be empty.", path, trace_id, "validation-error")
        if not _is_supported_upload(upload.name, upload.content_type):
            return _problem_response(
                422,
                "Unsupported file",
                "The public analysis entry supports text-like, PDF, email, archive, Office, OpenDocument, image, transcript, and bounded video inputs only.",
                path,
                trace_id,
                "unsupported-file",
            )

        session_id = session_id_from_headers(headers)
        reservation, capacity, capacity_code = self.capacity.try_begin(session_id)
        if capacity_code == "user-active":
            return _capacity_problem_response(
                409,
                "One analysis is already active",
                "The public analysis entry accepts one active file per browser session.",
                path,
                trace_id,
                "analysis-already-active",
                capacity,
            )
        if capacity_code == "capacity-full":
            return _capacity_problem_response(
                429,
                "Analysis capacity is full",
                "All public analysis slots are currently busy. Try again when a slot opens.",
                path,
                trace_id,
                "analysis-capacity-full",
                capacity,
            )
        assert reservation is not None

        try:
            result = _analyze_upload(upload)
        except DocumentExtractionIssue as error:
            self.capacity.finish(reservation)
            payload = problem(
                status=422,
                title="File could not be analyzed",
                detail=error.detail,
                instance=path,
                trace_id=trace_id,
                code="unsupported-file",
            )
            payload["capacity"] = self.capacity.status(session_id)
            return response(422, payload, trace_id, content_type="application/problem+json")
        except Exception as error:
            self.capacity.finish(reservation)
            payload = problem(
                status=500,
                title="Analysis failed",
                detail=str(error),
                instance=path,
                trace_id=trace_id,
                code="analysis-failed",
            )
            payload["capacity"] = self.capacity.status(session_id)
            return response(500, payload, trace_id, content_type="application/problem+json")

        self.capacity.finish(reservation)
        result["capacity"] = self.capacity.status(session_id)
        return response(200, envelope(result, trace_id), trace_id)


def session_id_from_headers(headers: dict[str, str]) -> str:
    raw = _header(headers, TRIAL_SESSION_HEADER) or _header(headers, "X-Actor-Id") or "anonymous-public-trial"
    return _SAFE_SESSION_RE.sub("_", raw.strip())[:96] or "anonymous-public-trial"


def _analyze_upload(upload: UploadFile) -> dict[str, Any]:
    extracted = extract_document_content(body=upload.body, content_type=upload.content_type, name=upload.name)
    signals = [
        sanitize_public_signal(signal)
        for signal in apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
    ]
    detected_types = _detected_types(signals)
    risk_level = _risk_level(detected_types)
    analysis_id = _analysis_id(upload)

    return {
        "analysisId": analysis_id,
        "status": "completed",
        "file": {
            "name": upload.name,
            "sizeBytes": len(upload.body),
            "fileFormat": extracted.file_format,
            "extractionMethod": extracted.extraction_method,
            "recognitionDifficulty": extracted.recognition_difficulty,
        },
        "summary": {
            "detectedSignalCount": len(signals),
            "detectedTypes": detected_types,
            "riskLevel": risk_level,
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
        "evidence": [_public_evidence(signal) for signal in signals[:5]],
        "warnings": _result_warnings(extracted.recognition_difficulty, len(signals)),
    }


def _parse_upload(body: bytes, content_type: str) -> UploadFile | dict[str, Any]:
    try:
        raw_message = b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
        message = BytesParser(policy=default).parsebytes(raw_message)
    except Exception:
        return _upload_error("Malformed multipart upload", "The upload body could not be parsed as multipart/form-data.", "malformed-upload")

    if not message.is_multipart():
        return _upload_error("Malformed multipart upload", "The upload body must contain one multipart file field.", "malformed-upload")

    file_parts: list[UploadFile] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "file":
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append(UploadFile(_safe_filename(part.get_filename()), part.get_content_type() or "application/octet-stream", payload))

    if not file_parts:
        return _upload_error("Request validation failed", "Upload must include a file field named file.", "validation-error")
    if len(file_parts) > 1:
        return _upload_error("Request validation failed", "Only one uploaded file is accepted per analysis.", "validation-error")
    return file_parts[0]


def _upload_error(title: str, detail: str, code: str) -> dict[str, Any]:
    return {"status": 422, "title": title, "detail": detail, "code": code}


def _safe_filename(filename: str | None) -> str:
    name = PurePath((filename or "uploaded-file.txt").replace("\\", "/")).name.strip()
    cleaned = "".join(character for character in name if character.isprintable() and character not in {"/", "\\"}).strip()
    return (cleaned or "uploaded-file.txt")[:140]


def _is_supported_upload(name: str, content_type: str) -> bool:
    suffix = Path(name).suffix.lower()
    normalized_type = content_type.lower().split(";", 1)[0].strip()
    if suffix in SUPPORTED_SUFFIXES:
        return True
    if normalized_type.startswith("text/") or normalized_type.startswith("video/"):
        return True
    if normalized_type in _PUBLIC_DOCUMENT_CONTENT_TYPES:
        return True
    return not suffix and normalized_type in SNIFFABLE_TEXT_CONTENT_TYPES


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


def _risk_level(detected_types: list[dict[str, Any]]) -> str:
    return public_risk_level({str(item["type"]) for item in detected_types})


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
    readiness = [
        "Redacted evidence is ready for human review.",
        "Raw source content is not returned in the public response.",
    ]
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
        {
            "name": "File intake",
            "status": "completed",
            "description": f"{file_format or 'file'} input accepted inside the one-file, 10 MB boundary.",
        },
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
    return {
        "type": signal.get("type") or "unknown",
        "detector": signal.get("detector") or "unknown",
        "confidence": round(float(signal.get("confidence") or 0), 2),
        "snippet": str(signal.get("snippet") or "[REDACTED_VALUE]")[:180],
        "locationLabel": fallback.get("label") or anchor.get("label") or "Detected text",
    }


def _result_warnings(recognition_difficulty: str, signal_count: int) -> list[str]:
    warnings: list[str] = []
    if recognition_difficulty in {"hard", "unsupported"}:
        warnings.append("Extraction required a hard recognition path; review coverage before relying on the result.")
    if signal_count == 0:
        warnings.append("No deterministic signal match is not proof that the file contains no personal data.")
    return warnings


def _analysis_id(upload: UploadFile) -> str:
    digest = hashlib.sha256(upload.name.encode("utf-8") + upload.body[:65_536]).hexdigest()[:12]
    return f"analysis_{int(time.time() * 1000)}_{digest}"


def _header(headers: dict[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def _too_large_response(path: str, trace_id: str, capacity: dict[str, Any]) -> dict[str, Any]:
    return _capacity_problem_response(
        413,
        "File too large",
        "The public analysis entry accepts one file up to 10 MB.",
        path,
        trace_id,
        "file-too-large",
        capacity,
    )


def _problem_response(status: int, title: str, detail: str, path: str, trace_id: str, code: str) -> dict[str, Any]:
    return response(
        status,
        problem(status=status, title=title, detail=detail, instance=path, trace_id=trace_id, code=code),
        trace_id,
        content_type="application/problem+json",
    )


def _capacity_problem_response(
    status: int,
    title: str,
    detail: str,
    path: str,
    trace_id: str,
    code: str,
    capacity: dict[str, Any],
) -> dict[str, Any]:
    payload = problem(status=status, title=title, detail=detail, instance=path, trace_id=trace_id, code=code)
    payload["capacity"] = capacity
    return response(status, payload, trace_id, content_type="application/problem+json")
