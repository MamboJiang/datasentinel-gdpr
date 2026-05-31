"""Source API facade used by HTTP routes and tests."""

from __future__ import annotations

from typing import Any

from .envelope import envelope, problem, response
from .google_drive_config import picker_config_from_env
from .source_connection import ConnectionIssue, SourceConnectionService
from .source_documents import SourceReadIssue, validate_remote_source_url
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

        safe_config = _safe_source_config(payload)
        source = {
            "sourceId": payload["sourceId"],
            "name": payload["name"],
            "sourceType": payload["sourceType"],
            "status": _initial_status(payload),
            **({"rootLabel": payload["rootLabel"]} if "rootLabel" in payload else {}),
            **({"masterOfDataUserId": payload["masterOfDataUserId"]} if "masterOfDataUserId" in payload else {}),
            **({"referenceUrl": payload["referenceUrl"]} if "referenceUrl" in payload else {}),
            **({"sampleFamilies": payload["sampleFamilies"]} if "sampleFamilies" in payload else {}),
            **({"config": safe_config} if safe_config else {}),
        }
        return response(201, envelope(self.store.add(source), trace_id), trace_id)

    def delete_source(self, source_id: str, trace_id: str, path: str | None = None) -> dict[str, Any]:
        deleted = self.store.delete(source_id)
        if not deleted:
            return response(
                404,
                problem(
                    status=404,
                    title="Source not found",
                    detail="The requested source registration does not exist.",
                    instance=path or f"/api/sources/{source_id}",
                    trace_id=trace_id,
                    code="source-not-found",
                ),
                trace_id,
                content_type="application/problem+json",
            )
        return response(200, envelope(deleted, trace_id), trace_id)

    def connection_envelope(self, source_id: str, trace_id: str) -> dict[str, Any]:
        data, partial, warnings = self.service.connection_result(source_id)
        return envelope(data, trace_id, partial=partial, warnings=warnings)

    def test_connection(self, source_id: str, trace_id: str, path: str | None = None) -> dict[str, Any]:
        try:
            payload = self.connection_envelope(source_id, trace_id)
            data = payload["data"]
            if data.get("reachable") and data.get("connectionStatus") == "connected":
                capabilities = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
                status = "authorization_required" if capabilities.get("requiresPerScanAccessToken") else "connected"
                self.store.add({key: value for key, value in data.items() if key not in {"reachable", "connectionStatus", "capabilities", "diagnostics"}} | {"status": status})
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

    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_type = payload.get("sourceType")

    if source_type == "remote_file_link":
        if not isinstance(config.get("url"), str):
            errors.append({"pointer": "#/config/url", "detail": "remote_file_link requires config.url"})
        else:
            try:
                validate_remote_source_url(config["url"])
            except SourceReadIssue as issue:
                errors.append({"pointer": issue.pointer, "detail": issue.detail})

    if source_type == "google_drive_selection":
        items = config.get("items")
        if not isinstance(items, list) or not items:
            errors.append({"pointer": "#/config/items", "detail": "google_drive_selection requires selected Drive items"})
        else:
            for index, item in enumerate(items):
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
                    errors.append({"pointer": f"#/config/items/{index}/id", "detail": "Google Drive selected items require an id"})
                if isinstance(item, dict) and "mimeType" in item and not isinstance(item["mimeType"], str):
                    errors.append({"pointer": f"#/config/items/{index}/mimeType", "detail": "Google Drive selected item mimeType must be a string"})

    return errors


def _initial_status(payload: dict[str, Any]) -> str:
    source_type = payload.get("sourceType")
    if source_type == "local_repo":
        return "registered"
    if source_type == "remote_file_link":
        return "connected"
    if source_type == "google_drive_selection":
        return "authorization_required" if picker_config_from_env()["configured"] else "registered"
    return str(payload.get("status") or "registered")


def _safe_source_config(payload: dict[str, Any]) -> dict[str, Any] | None:
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_type = payload.get("sourceType")

    if source_type == "local_repo" and isinstance(config.get("rootPath"), str):
        return {"rootPath": config["rootPath"].strip()}

    if source_type == "remote_file_link" and isinstance(config.get("url"), str):
        safe_config = {"url": config["url"].strip()}
        if isinstance(config.get("fileName"), str) and config["fileName"].strip():
            safe_config["fileName"] = config["fileName"].strip()
        return safe_config

    if source_type == "google_drive_selection" and isinstance(config.get("items"), list):
        return {"items": [_safe_drive_item(item) for item in config["items"] if isinstance(item, dict)]}

    return None


def _safe_drive_item(item: dict[str, Any]) -> dict[str, str]:
    safe_item: dict[str, str] = {}
    for key in ("id", "name", "mimeType", "url"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            safe_item[key] = value.strip()
    return safe_item
