"""Source API facade used by HTTP routes and tests."""

from __future__ import annotations

from typing import Any

from .envelope import envelope, problem, response
from .source_connection import ConnectionIssue, SourceConnectionService
from .source_store import SourceStore


class SourceApi:
    def __init__(
        self,
        service: SourceConnectionService | None = None,
        store: SourceStore | None = None,
    ) -> None:
        self.store = store or SourceStore()
        self.service = service or SourceConnectionService(self.store)

    def list_sources(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.store.list_sources(), trace_id), trace_id)

    def create_source(self, payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
        validation = _validate_source(payload)

        if validation:
            return response(
                422,
                problem(
                    status=422,
                    title="Request validation failed",
                    detail="The source request body is invalid.",
                    instance="/api/sources",
                    trace_id=trace_id,
                    code="validation-error",
                    errors=validation,
                ),
                trace_id,
                content_type="application/problem+json",
            )

        source = {
            "sourceId": payload["sourceId"],
            "name": payload["name"],
            "sourceType": payload["sourceType"],
            "status": payload.get("status", "registered"),
            **({"rootLabel": payload["rootLabel"]} if "rootLabel" in payload else {}),
            **({"masterOfDataUserId": payload["masterOfDataUserId"]} if "masterOfDataUserId" in payload else {}),
            **({"referenceUrl": payload["referenceUrl"]} if "referenceUrl" in payload else {}),
            **({"sampleFamilies": payload["sampleFamilies"]} if "sampleFamilies" in payload else {}),
            **({"config": payload["config"]} if "config" in payload else {}),
        }
        return response(201, envelope(self.store.add(source), trace_id), trace_id)

    def connection_envelope(self, source_id: str, trace_id: str) -> dict[str, Any]:
        data, partial, warnings = self.service.connection_result(source_id)
        return envelope(data, trace_id, partial=partial, warnings=warnings)

    def test_connection(self, source_id: str, trace_id: str, path: str | None = None) -> dict[str, Any]:
        try:
            payload = self.connection_envelope(source_id, trace_id)
            data = payload["data"]
            if data.get("reachable") and data.get("connectionStatus") == "connected":
                self.store.add({key: value for key, value in data.items() if key not in {"reachable", "connectionStatus", "capabilities", "diagnostics"}} | {"status": "connected"})
            return response(200, payload, trace_id)
        except ConnectionIssue as issue:
            return response(
                issue.status,
                problem_from_issue(issue, path or f"/api/sources/{source_id}/connect-test", trace_id),
                trace_id,
                content_type="application/problem+json",
            )


def problem_from_issue(issue: ConnectionIssue, path: str, trace_id: str) -> dict[str, Any]:
    return problem(
        status=issue.status,
        title="Source connection failed",
        detail=issue.detail,
        instance=path,
        trace_id=trace_id,
        code=issue.code,
        errors=[{"pointer": issue.pointer, "detail": issue.detail}],
    )


def _validate_source(payload: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    for field in ("sourceId", "name", "sourceType"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            errors.append({"pointer": f"#/{field}", "detail": f"{field} is required"})

    if "sampleFamilies" in payload and not isinstance(payload["sampleFamilies"], list):
        errors.append({"pointer": "#/sampleFamilies", "detail": "sampleFamilies must be an array"})

    if "config" in payload and not isinstance(payload["config"], dict):
        errors.append({"pointer": "#/config", "detail": "config must be an object"})

    return errors
