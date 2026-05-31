"""Workspace membership and invitation state for the local P0 API."""

from __future__ import annotations

import copy
import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from .envelope import envelope, response, utc_now
from .sqlite_store import SQLiteDocumentStore
from .workspace_commands import (
    group_id,
    group_with_name,
    parse_group_payload,
    require_workspace_permission,
    slug,
    stored_group,
    workspace_problem,
)
from .workspace_model import (
    account_payload,
    active_memberships,
    charts,
    current_membership,
    empty_admin_summary,
    expired,
    groups,
    matching_pending_invitations,
    memberships,
    permission_boundary,
    workspace,
    workspace_summary,
)
from .workspace_seed import (
    WORKSPACE_ADMIN_REQUIRED_PERMISSIONS,
    WORKSPACE_PERMISSION_OPTIONS,
    groups_for_workspace,
)
from .workspace_store import InMemoryWorkspaceStore, SQLiteWorkspaceStore, WorkspaceStore


class WorkspaceService:
    """Calculates Workspace membership, permissions, invitations, and admin charts."""

    def __init__(self, store: WorkspaceStore | None = None) -> None:
        self.store = store or InMemoryWorkspaceStore()

    @classmethod
    def with_sqlite(cls, documents: SQLiteDocumentStore) -> "WorkspaceService":
        return cls(SQLiteWorkspaceStore(documents))

    def directory(self, actor: dict[str, Any], trace_id: str) -> dict[str, Any]:
        state = self.store.load()
        memberships_for_actor = active_memberships(state, actor["accountId"])
        workspace_ids = {item["workspaceId"] for item in memberships_for_actor}
        invitations = matching_pending_invitations(state, actor)
        workspaces = [workspace_summary(state, item) for item in state["workspaces"] if item["workspaceId"] in workspace_ids]
        current = current_membership(state, actor["accountId"])

        return response(200, envelope({
            "account": account_payload(actor),
            "currentWorkspaceId": current["workspaceId"] if current else None,
            "workspaces": workspaces,
            "pendingInvitations": invitations,
            "workspaceRequired": not bool(workspaces),
        }, trace_id), trace_id)

    def create_workspace(self, payload: dict[str, Any], actor: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        state = self.store.load()
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip() or "Privacy operations workspace"

        if not name:
            return workspace_problem(422, "Workspace name is required.", path, trace_id, "#/name")

        workspace_slug = slug(name)
        if any(item["slug"] == workspace_slug for item in state["workspaces"]):
            return workspace_problem(409, "A Workspace with this name already exists.", path, trace_id, "#/name")

        now = utc_now()
        identity_seed = f"{actor['accountId']}:{name}:{now}"
        workspace_id = f"ws_{workspace_slug}_{hashlib.sha256(identity_seed.encode('utf-8')).hexdigest()[:8]}"
        state["workspaces"].append({
            "workspaceId": workspace_id,
            "name": name,
            "slug": workspace_slug,
            "status": "active",
            "plan": "Prelaunch",
            "description": description,
            "createdAt": now,
        })
        state["groups"].extend(groups_for_workspace(workspace_id))
        state["memberships"].append({
            "membershipId": f"mem_{actor['accountId']}_{workspace_id}",
            "workspaceId": workspace_id,
            "accountId": actor["accountId"],
            "displayName": actor["displayName"],
            "email": actor.get("email"),
            "groupIds": ["workspace_admin"],
            "status": "active",
            "joinedAt": now,
            "invitedBy": None,
            "lastActiveAt": now,
        })
        self.store.save(state)
        result = self.directory(actor, trace_id)
        result["status"] = 201
        return result

    def admin_summary(self, actor: dict[str, Any], metrics: dict[str, Any], trace_id: str) -> dict[str, Any]:
        state = self.store.load()
        membership = current_membership(state, actor["accountId"])
        current_workspace = workspace(state, membership["workspaceId"]) if membership else None
        boundary = permission_boundary(state, actor, membership)

        if not current_workspace or "view_workspace_admin" not in boundary["allowedActions"]:
            return response(200, envelope(empty_admin_summary(actor, current_workspace, membership, boundary), trace_id), trace_id)

        workspace_id = current_workspace["workspaceId"]
        workspace_groups = groups(state, workspace_id)
        members = memberships(state, workspace_id)
        invitations = [copy.deepcopy(item) for item in state["invitations"] if item["workspaceId"] == workspace_id]

        return response(200, envelope({
            "workspace": workspace_summary(state, current_workspace),
            "currentMembership": copy.deepcopy(membership),
            "permissionBoundary": boundary,
            "availablePermissions": copy.deepcopy(WORKSPACE_PERMISSION_OPTIONS),
            "groups": workspace_groups,
            "members": members,
            "invitations": invitations,
            "charts": charts(workspace_groups, invitations, metrics),
        }, trace_id), trace_id)

    def create_group(
        self,
        workspace_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_groups", path, trace_id)
        if access_problem:
            return access_problem

        parsed = parse_group_payload(payload, path, trace_id)
        if "body" in parsed:
            return parsed

        duplicate = group_with_name(state, workspace_id, parsed["name"], None)
        if duplicate:
            return workspace_problem(409, "A Workspace group with this name already exists.", path, trace_id, "#/name")

        group = {
            "workspaceId": workspace_id,
            "groupId": group_id(parsed["name"], groups(state, workspace_id)),
            "name": parsed["name"],
            "description": parsed["description"],
            "permissions": parsed["permissions"],
        }
        state["groups"].append(group)
        self.store.save(state)
        return response(201, envelope({**copy.deepcopy(group), "memberCount": 0}, trace_id), trace_id)

    def update_group(
        self,
        workspace_id: str,
        selected_group_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_groups", path, trace_id)
        if access_problem:
            return access_problem

        group = stored_group(state, workspace_id, selected_group_id)
        if not group:
            return workspace_problem(404, "Workspace group was not found.", path, trace_id, "#/groupId")

        parsed = parse_group_payload(payload, path, trace_id)
        if "body" in parsed:
            return parsed

        duplicate = group_with_name(state, workspace_id, parsed["name"], selected_group_id)
        if duplicate:
            return workspace_problem(409, "A Workspace group with this name already exists.", path, trace_id, "#/name")

        if selected_group_id == "workspace_admin":
            missing_required = [item for item in WORKSPACE_ADMIN_REQUIRED_PERMISSIONS if item not in parsed["permissions"]]
            if missing_required:
                detail = f"Workspace admin group must retain {missing_required[0]}."
                return workspace_problem(422, detail, path, trace_id, "#/permissions")

        group["name"] = parsed["name"]
        group["description"] = parsed["description"]
        group["permissions"] = parsed["permissions"]
        self.store.save(state)
        updated = next(item for item in groups(state, workspace_id) if item["groupId"] == selected_group_id)
        return response(200, envelope(updated, trace_id), trace_id)

    def delete_group(
        self,
        workspace_id: str,
        selected_group_id: str,
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_groups", path, trace_id)
        if access_problem:
            return access_problem

        group = stored_group(state, workspace_id, selected_group_id)
        if not group:
            return workspace_problem(404, "Workspace group was not found.", path, trace_id, "#/groupId")

        if selected_group_id == "workspace_admin":
            return workspace_problem(409, "Workspace admin group cannot be deleted.", path, trace_id, "#/groupId")

        member_count = sum(
            selected_group_id in member.get("groupIds", [])
            for member in state["memberships"]
            if member["workspaceId"] == workspace_id and member["status"] == "active"
        )
        deleted = {**copy.deepcopy(group), "memberCount": member_count, "status": "deleted"}
        now = utc_now()

        state["groups"] = [
            item for item in state["groups"]
            if not (item["workspaceId"] == workspace_id and item["groupId"] == selected_group_id)
        ]
        for member in state["memberships"]:
            if member["workspaceId"] == workspace_id and selected_group_id in member.get("groupIds", []):
                member["groupIds"] = [item for item in member["groupIds"] if item != selected_group_id]
        for invitation in state["invitations"]:
            if invitation["workspaceId"] != workspace_id or selected_group_id not in invitation.get("groupIds", []):
                continue
            invitation["groupIds"] = [item for item in invitation["groupIds"] if item != selected_group_id]
            if invitation["status"] == "pending" and not invitation["groupIds"]:
                invitation["status"] = "revoked"
                invitation["revokedAt"] = now

        self.store.save(state)
        return response(200, envelope(deleted, trace_id), trace_id)

    def create_invitation(
        self,
        workspace_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        membership = current_membership(state, actor["accountId"], workspace_id)
        boundary = permission_boundary(state, actor, membership)

        if "invite_workspace_members" not in boundary["allowedActions"]:
            return workspace_problem(403, "Workspace admin permission is required.", path, trace_id, "#/workspaceId")

        group_ids = payload.get("groupIds")

        if not isinstance(group_ids, list) or not group_ids or not all(isinstance(item, str) and item for item in group_ids):
            return workspace_problem(422, "At least one Workspace group is required.", path, trace_id, "#/groupIds")

        unique_group_ids = list(dict.fromkeys(group_ids))
        valid_group_ids = {group["groupId"] for group in groups(state, workspace_id)}
        unknown_group_ids = [group_id for group_id in unique_group_ids if group_id not in valid_group_ids]
        if unknown_group_ids:
            return workspace_problem(422, f"Unknown Workspace group: {unknown_group_ids[0]}", path, trace_id, "#/groupIds")

        now = datetime.now(UTC).replace(microsecond=0)
        invitation_id = f"invite_{int(time.time() * 1000)}_{secrets.token_urlsafe(12)}"
        invitation = {
            "invitationId": invitation_id,
            "workspaceId": workspace_id,
            "invitePath": f"/workspace/invitations/{invitation_id}",
            "groupIds": unique_group_ids,
            "status": "pending",
            "invitedBy": actor["accountId"],
            "invitedByDisplayName": actor["displayName"],
            "createdAt": now.isoformat().replace("+00:00", "Z"),
            "expiresAt": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
            "acceptedAt": None,
        }
        state["invitations"].insert(0, invitation)
        self.store.save(state)
        return response(201, envelope(invitation, trace_id), trace_id)

    def accept_invitation(self, invitation_id: str, actor: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        state = self.store.load()
        invitation = next((item for item in state["invitations"] if item["invitationId"] == invitation_id), None)

        if not invitation:
            return workspace_problem(404, "Workspace invitation was not found.", path, trace_id, "#/invitationId")

        if invitation["status"] != "pending":
            return workspace_problem(409, "Workspace invitation is no longer pending.", path, trace_id, "#/invitationId")

        if current_membership(state, actor["accountId"], invitation["workspaceId"]):
            return workspace_problem(409, "Account is already a member of this Workspace.", path, trace_id, "#/invitationId")

        if expired(invitation["expiresAt"]):
            invitation["status"] = "expired"
            self.store.save(state)
            return workspace_problem(409, "Workspace invitation has expired.", path, trace_id, "#/invitationId")

        now = utc_now()
        invitation["status"] = "accepted"
        invitation["acceptedAt"] = now
        state["memberships"].append({
            "membershipId": f"mem_{actor['accountId']}_{invitation['workspaceId']}",
            "workspaceId": invitation["workspaceId"],
            "accountId": actor["accountId"],
            "displayName": actor["displayName"],
            "email": actor.get("email"),
            "groupIds": invitation["groupIds"],
            "status": "active",
            "joinedAt": now,
            "invitedBy": invitation["invitedBy"],
            "lastActiveAt": now,
        })
        self.store.save(state)
        return self.directory(actor, trace_id)


def actor_from_headers(headers: dict[str, str], session_payload: dict[str, Any]) -> dict[str, Any]:
    user = session_payload.get("user") if session_payload.get("authenticated") else None
    if isinstance(user, dict) and isinstance(user.get("userId"), str) and user["userId"]:
        return {
            "accountId": user["userId"],
            "displayName": str(user.get("displayName") or user["userId"]),
            "email": user.get("email"),
        }

    actor_id = headers.get("X-Actor-Id") or "user_demo_admin"
    return {
        "accountId": actor_id,
        "displayName": "Demo Workspace Admin" if actor_id == "user_demo_admin" else actor_id,
        "email": "demo.admin@example.invalid" if actor_id == "user_demo_admin" else None,
    }
