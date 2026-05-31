"""HTTP routing for the DataSentinel local API server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .auth import AuthService
from .demo_state import DemoState
from .envelope import envelope, problem, response
from .google_drive_binding import GoogleDriveBindingService
from .google_drive_config import picker_config_response
from .persistent_demo_state import PersistentDemoState, PersistentPrelaunchState
from .prelaunch_state import PrelaunchState
from .source_api import SourceApi
from .source_connection import ConnectionPolicy, SourceConnectionService
from .source_store import SourceStore, demo_fixtures_enabled
from .sqlite_store import SQLiteAuthStore, SQLiteDocumentStore, SQLiteDriveBindingStore, SQLiteSourceStore, SQLiteWorkflowStore
from .workspace import WorkspaceService, actor_from_headers


@dataclass(frozen=True)
class SourceHttpOptions:
    sqlite_documents: SQLiteDocumentStore | None = None
    allowed_roots: list[Path | str] | None = None


class SourceHttpApp:
    def __init__(
        self,
        source_api: SourceApi | None = None,
        demo_state: DemoState | None = None,
        auth_service: AuthService | None = None,
        drive_binding_service: GoogleDriveBindingService | None = None,
        options: SourceHttpOptions | None = None,
    ) -> None:
        runtime_options = options or SourceHttpOptions()
        self.source_api = source_api or SourceApi()
        self.demo_state = demo_state or (DemoState(self.source_api.store) if demo_fixtures_enabled() else PrelaunchState(self.source_api.store))
        self.auth_service = auth_service or AuthService()
        self.drive_binding_service = drive_binding_service or GoogleDriveBindingService(settings=self.auth_service.settings)
        self.sqlite_documents = runtime_options.sqlite_documents
        self.allowed_roots = runtime_options.allowed_roots or []
        self.workspace_service = WorkspaceService.with_sqlite(self.sqlite_documents) if self.sqlite_documents else WorkspaceService()

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
        drive_binding_service = GoogleDriveBindingService(SQLiteDriveBindingStore(documents), auth_service.settings)
        return cls(auth_service=auth_service, drive_binding_service=drive_binding_service, options=SourceHttpOptions(sqlite_documents=documents, allowed_roots=roots))

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

        if method == "GET" and route == "/integrations/google-drive/binding":
            user = self._session_user(headers)
            return self.drive_binding_service.status(user, trace_id, f"/api{route}")

        if method == "POST" and route == "/integrations/google-drive/picker-token":
            user = self._session_user(headers)
            return self.drive_binding_service.picker_token(user, trace_id, f"/api{route}")

        if method == "GET" and route == "/integrations/google-drive/bind/start":
            user = self._session_user(headers)
            return self.drive_binding_service.start_binding(user, trace_id, f"/api{route}")

        if method == "GET" and route == "/integrations/google-drive/bind/callback":
            user = self._session_user(headers)
            return self.drive_binding_service.complete_callback(query, headers, user, trace_id)

        if method == "DELETE" and route == "/integrations/google-drive/binding":
            user = self._session_user(headers)
            return self.drive_binding_service.disconnect(user, trace_id, f"/api{route}")

        if method == "GET" and route == "/health":
            return self.demo_state.health(trace_id)

        auth_required = self.auth_service.require_session(headers, trace_id, f"/api{route}")
        if auth_required:
            return auth_required

        actor = actor_from_headers(headers, self.auth_service.session_payload(headers))

        if method == "GET" and route == "/workspaces":
            return self.workspace_service.directory(actor, trace_id)

        if method == "POST" and route == "/workspaces":
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.create_workspace(payload_response["payload"], actor, trace_id, f"/api{route}")

        if method == "POST" and route == "/workspaces/current":
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.switch_workspace(payload_response["payload"], actor, trace_id, f"/api{route}")

        if method == "GET" and route == "/workspaces/current/admin":
            _source_api, demo_state = self._scoped_runtime(headers, actor)
            return self.workspace_service.admin_summary(actor, getattr(demo_state, "metrics", {}), trace_id)

        workspace_owner_transfer = _match(route, "/workspaces/", "/owner-transfer")
        if method == "POST" and workspace_owner_transfer:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.transfer_owner(workspace_owner_transfer, payload_response["payload"], actor, trace_id, f"/api{route}")

        workspace_item = _workspace_item_match(route)
        if workspace_item and method in {"PATCH", "DELETE"}:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            if method == "PATCH":
                return self.workspace_service.update_workspace_settings(workspace_item, payload_response["payload"], actor, trace_id, f"/api{route}")
            return self.workspace_service.delete_workspace(workspace_item, payload_response["payload"], actor, trace_id, f"/api{route}")

        workspace_group_collection = _match(route, "/workspaces/", "/groups")
        if method == "POST" and workspace_group_collection:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.create_group(workspace_group_collection, payload_response["payload"], actor, trace_id, f"/api{route}")

        workspace_group = _workspace_group_match(route)
        if workspace_group and method in {"PATCH", "DELETE"}:
            workspace_id, group_id = workspace_group
            if method == "DELETE":
                return self.workspace_service.delete_group(workspace_id, group_id, actor, trace_id, f"/api{route}")
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.update_group(workspace_id, group_id, payload_response["payload"], actor, trace_id, f"/api{route}")

        workspace_member = _workspace_member_match(route)
        if workspace_member and method in {"PATCH", "DELETE"}:
            workspace_id, membership_id = workspace_member
            if method == "DELETE":
                return self.workspace_service.remove_member(workspace_id, membership_id, actor, trace_id, f"/api{route}")
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.update_member(workspace_id, membership_id, payload_response["payload"], actor, trace_id, f"/api{route}")

        accept_invitation = _match(route, "/workspaces/invitations/", "/accept")
        if method == "POST" and accept_invitation:
            return self.workspace_service.accept_invitation(accept_invitation, actor, trace_id, f"/api{route}")

        workspace_invitation = _match(route, "/workspaces/", "/invitations")
        if method == "POST" and workspace_invitation:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            return self.workspace_service.create_invitation(workspace_invitation, payload_response["payload"], actor, trace_id, f"/api{route}")

        source_api, demo_state = self._scoped_runtime(headers, actor)
        workflow_context = self.workspace_service.workflow_context(actor)
        workflow_access_context = workflow_context if isinstance(demo_state, PrelaunchState) else None

        if method == "GET" and route == "/integrations/google-drive/picker-config":
            return picker_config_response(trace_id)

        if method == "GET" and route == "/sources":
            result = source_api.list_sources(trace_id)
            result["body"]["data"] = _visible_sources(result["body"]["data"], workflow_access_context) if workflow_access_context else result["body"]["data"]
            return result

        if method == "POST" and route == "/sources":
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            assigned_payload = _source_assignment_payload(payload_response["payload"], workflow_context, trace_id, f"/api{route}")
            if "body" in assigned_payload:
                return assigned_payload
            return source_api.create_source(assigned_payload["payload"], trace_id)

        source_id = _match(route, "/sources/")
        if method == "PATCH" and source_id and "/" not in source_id:
            access_problem = _require_source_admin(workflow_context, trace_id, f"/api{route}")
            if access_problem:
                return access_problem
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            assigned_payload = _source_assignment_payload(payload_response["payload"], workflow_context, trace_id, f"/api{route}")
            if "body" in assigned_payload:
                return assigned_payload
            result = source_api.update_source(source_id, assigned_payload["payload"], trace_id, f"/api{route}")
            if result["status"] < 400:
                source_assignment_changed = getattr(demo_state, "source_assignment_changed", None)
                if callable(source_assignment_changed):
                    source_assignment_changed(result["body"]["data"])
            return result

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
            source_id_for_scan = payload_response["payload"].get("sourceId")
            if isinstance(source_id_for_scan, str):
                source = source_api.store.get(source_id_for_scan)
                if workflow_access_context and source and source not in _visible_sources([source], workflow_access_context):
                    return _source_access_problem(trace_id, f"/api{route}")
                if source and source.get("sourceType") == "google_drive_selection" and not _has_google_drive_access_token(payload_response["payload"]):
                    access_token = self.drive_binding_service.access_token(self._session_user(headers))
                    if access_token:
                        payload_response["payload"] = _with_google_drive_access_token(payload_response["payload"], access_token)
            scan_type = "delta" if route.endswith("/delta") else "full"
            return demo_state.start_scan(scan_type, payload_response["payload"], trace_id, f"/api{route}")

        scan_summary = _match(route, "/scans/", "/summary")
        if method == "GET" and scan_summary:
            return demo_state.get_scan_summary(trace_id)

        scan_id = _match(route, "/scans/")
        if method == "GET" and scan_id:
            return demo_state.get_scan(scan_id, trace_id, f"/api{route}")

        if method == "GET" and route == "/findings":
            return demo_state.list_findings(trace_id, workflow_access_context)

        review_support = _match(route, "/findings/", "/review-support")
        if method == "GET" and review_support:
            return demo_state.finding_review_support(review_support, trace_id, f"/api{route}", workflow_access_context)

        review_finding = _match(route, "/findings/", "/review")
        if method == "POST" and review_finding:
            payload_response = self._json_body(body, content_type, route, trace_id)
            if "body" in payload_response:
                return payload_response
            payload = {**payload_response["payload"], "findingId": review_finding}
            return demo_state.review_finding(review_finding, payload, trace_id, f"/api{route}", workflow_access_context)

        finding_id = _match(route, "/findings/")
        if method == "GET" and finding_id:
            return demo_state.get_finding(finding_id, trace_id, f"/api{route}", workflow_access_context)

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
            return demo_state.permissions(trace_id, workflow_context)

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

    def _scoped_runtime(self, headers: dict[str, str], actor: dict[str, Any] | None = None) -> tuple[SourceApi, DemoState]:
        if not self.sqlite_documents:
            return self.source_api, self.demo_state

        owner_id = self._request_owner_id(headers, actor)
        store = SQLiteSourceStore(self.sqlite_documents, allowed_roots=self.allowed_roots, owner_id=owner_id)
        policy = ConnectionPolicy.with_roots(self.allowed_roots)
        source_api = SourceApi(SourceConnectionService(store, policy), store)
        workflow_store = SQLiteWorkflowStore(self.sqlite_documents, owner_id)
        state = PersistentDemoState(store, workflow_store) if demo_fixtures_enabled() else PersistentPrelaunchState(store, workflow_store)
        return source_api, state

    def _request_owner_id(self, headers: dict[str, str], actor: dict[str, Any] | None = None) -> str:
        if actor:
            workspace_id = self.workspace_service.current_workspace_id(actor)
            if workspace_id:
                return f"workspace:{workspace_id}"

        session = self.auth_service.session_payload(headers)
        user = session.get("user") if session.get("authenticated") else None
        if isinstance(user, dict) and isinstance(user.get("userId"), str) and user["userId"]:
            return f"account:{user['userId']}"
        return "anonymous"

    def _session_user(self, headers: dict[str, str]) -> dict[str, Any] | None:
        session = self.auth_service.session_payload(headers)
        user = session.get("user") if session.get("authenticated") else None
        return user if isinstance(user, dict) and isinstance(user.get("userId"), str) else None


def _source_assignment_payload(
    payload: dict[str, Any],
    workflow_context: dict[str, Any],
    trace_id: str,
    path: str,
) -> dict[str, Any]:
    next_payload = dict(payload)
    members = workflow_context.get("members") if isinstance(workflow_context.get("members"), list) else []
    members_by_id = {member["accountId"]: member for member in members if isinstance(member.get("accountId"), str)}
    assignment_field_present = "assignedOwnerUserId" in payload
    selected_owner = _optional_text(payload.get("assignedOwnerUserId")) if assignment_field_present else None
    actor_id = (workflow_context.get("actor") or {}).get("accountId")

    if not assignment_field_present and isinstance(actor_id, str) and actor_id in members_by_id:
        assignment_field_present = True
        selected_owner = actor_id

    if selected_owner and selected_owner not in members_by_id:
        return response(
            422,
            problem(
                status=422,
                title="Request validation failed",
                detail="Source owner must be an active member of the current Workspace.",
                instance=path,
                trace_id=trace_id,
                code="validation-error",
                errors=[{"pointer": "#/assignedOwnerUserId", "detail": "Source owner must be an active member of the current Workspace."}],
            ),
            trace_id,
            content_type="application/problem+json",
        )

    if assignment_field_present:
        next_payload["assignedOwnerUserId"] = selected_owner
        next_payload["masterOfDataUserId"] = selected_owner
        if selected_owner:
            next_payload["assignedOwner"] = _member_owner(members_by_id[selected_owner], "direct_owner", "Source owner selected in Workspace Sources.")
        else:
            next_payload["assignedOwner"] = None

    fallback = _fallback_steward(members) if not selected_owner else None
    next_payload["fallbackOwner"] = fallback
    return {"payload": next_payload}


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _fallback_steward(members: list[dict[str, Any]]) -> dict[str, Any] | None:
    steward = next((member for member in members if "data_steward" in member.get("groupIds", [])), None)
    return _member_owner(steward, "data_steward_fallback", "No direct Source owner was selected; Data Steward fallback owns orphan findings.") if steward else None


def _member_owner(member: dict[str, Any], assignment_type: str, reason: str) -> dict[str, Any]:
    return {
        "userId": member["accountId"],
        "displayName": member.get("displayName") or member["accountId"],
        "email": member.get("email"),
        "assignmentType": assignment_type,
        "assignmentReason": reason,
        "assignmentSource": "source_assignment" if assignment_type == "direct_owner" else "data_steward_fallback",
    }


def _visible_sources(sources: list[dict[str, Any]], workflow_context: dict[str, Any]) -> list[dict[str, Any]]:
    if not workflow_context.get("workspace"):
        return sources

    boundary = workflow_context.get("permissionBoundary") or {}
    allowed = set(boundary.get("allowedActions") or [])
    if "view_workspace_admin" in allowed:
        return sources

    if not ({"view_owned_sources", "view_assigned_findings"} & allowed):
        return []

    actor_id = ((workflow_context.get("actor") or {}).get("accountId"))
    return [source for source in sources if _source_owner_id(source) == actor_id]


def _source_owner_id(source: dict[str, Any]) -> str | None:
    owner = source.get("assignedOwner")
    if isinstance(owner, dict) and isinstance(owner.get("userId"), str):
        return owner["userId"]
    if isinstance(source.get("assignedOwnerUserId"), str) and source["assignedOwnerUserId"].strip():
        return source["assignedOwnerUserId"].strip()
    fallback = source.get("fallbackOwner")
    if isinstance(fallback, dict) and isinstance(fallback.get("userId"), str):
        return fallback["userId"]
    if isinstance(source.get("masterOfDataUserId"), str) and source["masterOfDataUserId"].strip():
        return source["masterOfDataUserId"].strip()
    return None


def _require_source_admin(workflow_context: dict[str, Any], trace_id: str, path: str) -> dict[str, Any] | None:
    boundary = workflow_context.get("permissionBoundary") or {}
    if "view_workspace_admin" in set(boundary.get("allowedActions") or []):
        return None
    return response(
        403,
        problem(
            status=403,
            title="Workspace permission required",
            detail="Workspace admin permission is required to edit Source assignment.",
            instance=path,
            trace_id=trace_id,
            code="workspace-permission-required",
            errors=[{"pointer": "#/sourceId", "detail": "Workspace admin permission is required to edit Source assignment."}],
        ),
        trace_id,
        content_type="application/problem+json",
    )


def _source_access_problem(trace_id: str, path: str) -> dict[str, Any]:
    return response(
        403,
        problem(
            status=403,
            title="Source permission required",
            detail="The current Workspace member cannot access this Source.",
            instance=path,
            trace_id=trace_id,
            code="source-permission-required",
            errors=[{"pointer": "#/sourceId", "detail": "The current Workspace member cannot access this Source."}],
        ),
        trace_id,
        content_type="application/problem+json",
    )


def _has_google_drive_access_token(payload: dict[str, Any]) -> bool:
    authorization = payload.get("authorization")
    token = authorization.get("googleDriveAccessToken") if isinstance(authorization, dict) else None
    return isinstance(token, str) and bool(token.strip())


def _with_google_drive_access_token(payload: dict[str, Any], access_token: str) -> dict[str, Any]:
    authorization = payload.get("authorization") if isinstance(payload.get("authorization"), dict) else {}
    return {**payload, "authorization": {**authorization, "googleDriveAccessToken": access_token}}


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


def _workspace_group_match(route: str) -> tuple[str, str] | None:
    parts = route.strip("/").split("/")
    if len(parts) != 4 or parts[0] != "workspaces" or parts[2] != "groups":
        return None
    return unquote(parts[1]), unquote(parts[3])


def _workspace_member_match(route: str) -> tuple[str, str] | None:
    parts = route.strip("/").split("/")
    if len(parts) != 4 or parts[0] != "workspaces" or parts[2] != "members":
        return None
    return unquote(parts[1]), unquote(parts[3])


def _workspace_item_match(route: str) -> str | None:
    parts = route.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "workspaces":
        return None
    return unquote(parts[1])
