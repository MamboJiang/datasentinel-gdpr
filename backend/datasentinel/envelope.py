"""Contract envelope and problem-detail helpers for the demo API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

CONTRACT_VERSION = "0.1.0"
PROBLEM_BASE = "https://datasentinel.local/problems"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def meta(trace_id: str, *, partial: bool = False, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "contractVersion": CONTRACT_VERSION,
        "generatedAt": utc_now(),
        "traceId": trace_id,
        "partial": partial,
        "warnings": warnings or [],
    }


def envelope(
    data: Any,
    trace_id: str,
    *,
    pagination: dict[str, Any] | None = None,
    partial: bool = False,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "data": data,
        "meta": meta(trace_id, partial=partial, warnings=warnings),
    }

    if pagination is not None:
        payload["pagination"] = pagination

    return payload


def problem(
    *,
    status: int,
    title: str,
    detail: str,
    instance: str,
    trace_id: str,
    code: str = "request-error",
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "traceId": trace_id,
    }

    if errors:
        payload["errors"] = errors

    return payload


def response(
    status: int,
    body: dict[str, Any],
    trace_id: str,
    *,
    content_type: str = "application/json",
) -> dict[str, Any]:
    return {
        "status": status,
        "contentType": content_type,
        "headers": {
            "Content-Type": content_type,
            "X-Trace-Id": trace_id,
            "X-Contract-Version": CONTRACT_VERSION,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Accept, Content-Type, X-Actor-Id, X-Contract-Version, Idempotency-Key, X-Trace-Id",
            "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
        },
        "body": body,
    }
