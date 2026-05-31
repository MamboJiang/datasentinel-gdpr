"""HTTP routing for the DataSentinel local API server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .auth import AuthService
from .demo_state import DemoState
from .envelope import envelope, problem, response
from .google_drive_config import picker_config_response
from .persistent_demo_state import PersistentDemoState, PersistentPrelaunchState
from .prelaunch_state import PrelaunchState
from .source_api import SourceApi
from .source_connection import ConnectionPolicy, SourceConnectionService
from .source_store import SourceStore, demo_fixtures_enabled
from .sqlite_store import SQLiteAuthStore, SQLiteDocumentStore, SQLiteSourceStore, SQLiteWorkflowStore


class SourceHttpApp:
    def __init__(
        self,
        source_api: SourceApi | None = None,
        demo_state: DemoState | None = None,
        auth_service: AuthService | None = None,
        sqlite_documents: SQLiteDocumentStore | None = None,
        allowed_roots: list[Path | str] | None = None,
    ) -> None:
        self.source_api = source_api or SourceApi()
        self.demo_state = demo_state or (DemoState(self.source_api.store) if demo_fixtures_enabled() else PrelaunchState(self.source_api.store))
        self.auth_service = auth_service or AuthService()
        self.sqlite_documents = sqlite_documents
        self.allowed_roots = allowed_roots or []

    @classmethod
    def with_roots(cls, allowed_roots: list[Path | str]) -> "SourceHttpApp":
        store = SourceStore.with_roots(allowed_roots)
        policy = ConnectionPolicy.with_roots(allowed_roots)
        source_api = SourceApi(SourceConnectionService(store, policy), store)
        state = DemoState(store) if demo_fixtures_enabled() else PrelaunchState(store)
        return cls(source_api, state)

    @classmethod
    def with_sqlite(
        cls,
        db_path: Path | str,
        allowed_roots: list[Path | str] | None = None,
    ) -> "SourceHttpApp":
        roots = allowed_roots or []
        documents = SQLiteDocumentStore(db_path)
        auth_service = AuthService(SQLiteAuthStore(documents))
        return cls(auth_service=auth_service, sqlite_documents=documents, allowed_roots=roots)

    def handle(
        self,
        method: str,
        path: str,
        trace_id: str = "trace_demo_backend",
        body: str | bytes | None = None,
        content_type: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        parsed = urlparse(path)
        route = _normalise_path(parsed.path)
        query = parse_qs(parsed.query)
        method = method.upper()

        if method == "OPTIONS":
            return response(204, {}, trace_id)

        try:
            return self._route(method, route, query, trace_id, body, content_type, headers or {})
        except Exception as error:
            return response(
                500,
                problem(
                    status=500,
                    title="Backend route failed",
                    detail=str(error),
                    instance=parsed.path,
                    trace_id=trace_id,
                    code="internal-error",
                ),
                trace_id,
                content_type="application/problem+json",
            )

    def _route(
        self,
        method: str,
        route: str,
        query: dict[str, list[str]],
        trace_id: str,
        body: str | bytes | None,
        content_type: str | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        if method == "GET" and route == "/auth/providers":
            return self.auth_service.providers(trace_id)

        login_provider = _match(route, "/auth/login/")
        if method == "GET" and login_provider:
            return self.auth_service.start_login(login_provider, trace_id, f"/api{route}")

        callback_provider = _match(route, "/auth/callback/")
        if method == "GET" and callback_provider:
            return self.auth_service.complete_callback(callback_provider, query, headers, trace_id)

        if method == "GET" and route == "/auth/session":
            return self.auth_service.session(headers, trace_id)

        if method == "POST" and route == "/auth/logout":
            return self.auth_service.logout(headers, trace_id)

        if method == "GET" and route == "/health":
            return self.demo_state.health(trace_id)

        auth_required = self.auth_service.require_session(headers, trace_id, f"/api{route}")
        if auth_required:
            return auth_required

        source_api, demo_state = self._scoped_runtime(headers)

        if method == "GET" and route == "/integrations/google-drive/picker-config":
            return picker_config_response(trace_id)

        if method == "GET" and route == "/sources":
            return source_api.list_sources(trace_id)

        if method == "POST" and route == "/sources":
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return source_api.create_source(payload_response["payload"], trace_id)

        source_id = _match(route, "/sources/")
        if method == "DELETE" and source_id and "/" not in source_id:
            result = source_api.delete_source(source_id, trace_id, f"/api{route}")
            if result["status"] < 400:
                source_deleted = getattr(demo_state, "source_deleted", None)
                if callable(source_deleted):
                    source_deleted(source_id)
            return result

        source_connect = _match(route, "/sources/", "/connect-test")
        if method == "POST" and source_connect:
            return source_api.test_connection(source_connect, trace_id, f"/api{route}")

        if method == "POST" and route in {"/scans/full", "/scans/delta"}:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            scan_type = "delta" if route.endswith("/delta") else "full"
            return demo_state.start_scan(scan_type, payload_response["payload"], trace_id, f"/api{route}")

        scan_summary = _match(route, "/scans/", "/summary")
        if method == "GET" and scan_summary:
            return demo_state.get_scan_summary(trace_id)

        scan_id = _match(route, "/scans/")
        if method == "GET" and scan_id:
            return demo_state.get_scan(scan_id, trace_id, f"/api{route}")

        if method == "GET" and route == "/findings":
            return demo_state.list_findings(trace_id)

        review_support = _match(route, "/findings/", "/review-support")
        if method == "GET" and review_support:
            return demo_state.finding_review_support(review_support, trace_id, f"/api{route}")

        review_finding = _match(route, "/findings/", "/review")
        if method == "POST" and review_finding:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            payload = {**payload_response["payload"], "findingId": review_finding}
            return demo_state.review_finding(review_finding, payload, trace_id, f"/api{route}")

        finding_id = _match(route, "/findings/")
        if method == "GET" and finding_id:
            return demo_state.get_finding(finding_id, trace_id, f"/api{route}")

        if method == "GET" and route == "/audit/events":
            return demo_state.audit_event_list(trace_id)

        if method == "GET" and route == "/admin/metrics":
            return demo_state.admin_metrics(trace_id)

        if method == "GET" and route == "/evaluation/runs/latest":
            return demo_state.latest_evaluation(trace_id)

        if method == "GET" and route == "/governance/config":
            return demo_state.governance(trace_id)

        if method == "GET" and route == "/governance/policy-packs/active":
            return demo_state.active_policy_pack(trace_id)

        if method == "POST" and route == "/governance/changes/preview":
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return demo_state.governance_preview(trace_id)

        if method == "GET" and route == "/users/me/permissions":
            return demo_state.permissions(trace_id)

        return response(
            404,
            problem(
                status=404,
                title="Route not found",
                detail="The requested API route is not available.",
                instance=f"/api{route}",
                trace_id=trace_id,
                code="not-found",
            ),
            trace_id,
            content_type="application/problem+json",
        )

    def _json_body(
        self,
        body: str | bytes | None,
        content_type: str | None,
        route: str,
        trace_id: str,
    ) -> dict[str, Any]:
        if content_type and "application/json" not in content_type:
            return response(
                415,
                problem(
                    status=415,
                    title="Unsupported media type",
                    detail="POST requests require application/json.",
                    instance=f"/api{route}",
                    trace_id=trace_id,
                    code="unsupported-media-type",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        raw = body.decode("utf-8") if isinstance(body, bytes) else (body or "{}")

        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return response(
                400,
                problem(
                    status=400,
                    title="Malformed JSON",
                    detail="Request body must be valid JSON.",
                    instance=f"/api{route}",
                    trace_id=trace_id,
                    code="malformed-json",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        if not isinstance(payload, dict):
            return response(
                422,
                problem(
                    status=422,
                    title="Request validation failed",
                    detail="Request body must be a JSON object.",
                    instance=f"/api{route}",
                    trace_id=trace_id,
                    code="validation-error",
                    errors=[{"pointer": "#", "detail": "Request body must be a JSON object."}],
                ),
                trace_id,
                content_type="application/problem+json",
            )

        return {"payload": payload}

    def _scoped_runtime(self, headers: dict[str, str]) -> tuple[SourceApi, DemoState]:
        if not self.sqlite_documents:
            return self.source_api, self.demo_state

        owner_id = self._request_owner_id(headers)
        store = SQLiteSourceStore(self.sqlite_documents, allowed_roots=self.allowed_roots, owner_id=owner_id)
        policy = ConnectionPolicy.with_roots(self.allowed_roots)
        source_api = SourceApi(SourceConnectionService(store, policy), store)
        workflow_store = SQLiteWorkflowStore(self.sqlite_documents, owner_id)
        state = PersistentDemoState(store, workflow_store) if demo_fixtures_enabled() else PersistentPrelaunchState(store, workflow_store)
        return source_api, state

    def _request_owner_id(self, headers: dict[str, str]) -> str:
        session = self.auth_service.session_payload(headers)
        user = session.get("user") if session.get("authenticated") else None
        if isinstance(user, dict) and isinstance(user.get("userId"), str) and user["userId"]:
            return user["userId"]
        return "anonymous"


def build_default_app() -> SourceHttpApp:
    return SourceHttpApp()


def build_sqlite_app(db_path: Path | str, allowed_roots: list[Path | str] | None = None) -> SourceHttpApp:
    return SourceHttpApp.with_sqlite(db_path, allowed_roots)


def _normalise_path(path: str) -> str:
    route = path[:-1] if len(path) > 1 and path.endswith("/") else path
    return route[4:] if route.startswith("/api") else route


def _match(route: str, prefix: str, suffix: str = "") -> str | None:
    if not route.startswith(prefix):
        return None

    if suffix and not route.endswith(suffix):
        return None

    value = route[len(prefix):]

    if suffix:
        value = value[:-len(suffix)]

    return value.strip("/") or None
