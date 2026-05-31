"""Validation helpers for Workspace command handlers."""

from __future__ import annotations

import re
from typing import Any

from .envelope import problem, response
from .workspace_model import current_membership, permission_boundary, workspace
from .workspace_seed import WORKSPACE_PERMISSION_IDS

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(name: str) -> str:
    value = SLUG_RE.sub("-", name.lower()).strip("-")
    return value[:48] or "workspace"


def group_id(name: str, workspace_groups: list[dict[str, Any]]) -> str:
    base = f"custom_{slug(name)}"
    group_ids = {group["groupId"] for group in workspace_groups}
    candidate = base
    suffix = 2
    while candidate in group_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def stored_group(state: dict[str, Any], workspace_id: str, selected_group_id: str) -> dict[str, Any] | None:
    return next(
        (
            item for item in state["groups"]
            if item["workspaceId"] == workspace_id and item["groupId"] == selected_group_id
        ),
        None,
    )


def stored_membership(state: dict[str, Any], workspace_id: str, membership_id: str) -> dict[str, Any] | None:
    return next(
        (
            item for item in state["memberships"]
            if item["workspaceId"] == workspace_id
            and item["membershipId"] == membership_id
            and item["status"] == "active"
        ),
        None,
    )


def group_with_name(
    state: dict[str, Any],
    workspace_id: str,
    name: str,
    ignored_group_id: str | None,
) -> dict[str, Any] | None:
    normalized = name.casefold()
    return next(
        (
            item for item in state["groups"]
            if item["workspaceId"] == workspace_id
            and item["groupId"] != ignored_group_id
            and str(item["name"]).casefold() == normalized
        ),
        None,
    )


def require_workspace_permission(
    state: dict[str, Any],
    workspace_id: str,
    actor: dict[str, Any],
    permission: str,
    path: str,
    trace_id: str,
) -> dict[str, Any] | None:
    target_workspace = workspace(state, workspace_id)
    if not target_workspace or target_workspace.get("status") != "active":
        return workspace_problem(404, "Workspace was not found.", path, trace_id, "#/workspaceId")

    membership = current_membership(state, actor["accountId"], workspace_id)
    boundary = permission_boundary(state, actor, membership)
    if permission not in boundary["allowedActions"]:
        return workspace_problem(403, "Workspace permission is required.", path, trace_id, "#/workspaceId")

    return None


def parse_group_payload(payload: dict[str, Any], path: str, trace_id: str) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    description = str(payload.get("description") or "").strip()
    permissions = payload.get("permissions")

    if not name:
        return workspace_problem(422, "Workspace group name is required.", path, trace_id, "#/name")

    if not isinstance(permissions, list) or not all(isinstance(item, str) and item for item in permissions):
        return workspace_problem(
            422,
            "Workspace group permissions must be an array of permission strings.",
            path,
            trace_id,
            "#/permissions",
        )

    unique_permissions = list(dict.fromkeys(permissions))
    unknown_permissions = [item for item in unique_permissions if item not in WORKSPACE_PERMISSION_IDS]
    if unknown_permissions:
        return workspace_problem(422, f"Unknown Workspace permission: {unknown_permissions[0]}", path, trace_id, "#/permissions")

    return {
        "name": name,
        "description": description,
        "permissions": unique_permissions,
    }


def parse_member_group_payload(state: dict[str, Any], workspace_id: str, payload: dict[str, Any], path: str, trace_id: str) -> dict[str, Any]:
    group_ids = payload.get("groupIds")

    if not isinstance(group_ids, list) or not group_ids or not all(isinstance(item, str) and item for item in group_ids):
        return workspace_problem(422, "Workspace member groups must be a non-empty array.", path, trace_id, "#/groupIds")

    unique_group_ids = list(dict.fromkeys(group_ids))
    valid_group_ids = {
        group["groupId"] for group in state["groups"]
        if group["workspaceId"] == workspace_id
    }
    unknown_group_ids = [group_id for group_id in unique_group_ids if group_id not in valid_group_ids]
    if unknown_group_ids:
        return workspace_problem(422, f"Unknown Workspace group: {unknown_group_ids[0]}", path, trace_id, "#/groupIds")

    return {"groupIds": unique_group_ids}


def workspace_problem(status: int, detail: str, path: str, trace_id: str, pointer: str) -> dict[str, Any]:
    return response(
        status,
        problem(
            status=status,
            title="Workspace command rejected" if status != 422 else "Workspace validation failed",
            detail=detail,
            instance=path,
            trace_id=trace_id,
            code="workspace-error",
            errors=[{"pointer": pointer, "detail": detail}],
        ),
        trace_id,
        content_type="application/problem+json",
    )
