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
    parse_member_group_payload,
    require_workspace_permission,
    slug,
    stored_group,
    stored_membership,
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
    WORKSPACE_OWNER_REQUIRED_PERMISSIONS,
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
        workspaces = [
            workspace_summary(state, item) for item in state["workspaces"]
            if item["workspaceId"] in workspace_ids and item.get("status") == "active"
        ]
        current = current_membership(state, actor["accountId"])

        return response(200, envelope({
            "account": account_payload(actor),
            "currentWorkspaceId": current["workspaceId"] if current else None,
            "workspaces": workspaces,
            "pendingInvitations": invitations,
            "workspaceRequired": not bool(workspaces),
        }, trace_id), trace_id)

    def current_workspace_id(self, actor: dict[str, Any]) -> str | None:
        state = self.store.load()
        membership = current_membership(state, actor["accountId"])
        return membership["workspaceId"] if membership else None

    def create_workspace(self, payload: dict[str, Any], actor: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        state = self.store.load()
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip() or "Privacy operations workspace"

        if not name:
            return workspace_problem(422, "Workspace name is required.", path, trace_id, "#/name")

        workspace_slug = slug(name)
        if any(item["slug"] == workspace_slug and item.get("status") == "active" for item in state["workspaces"]):
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
            "groupIds": ["workspace_owner", "workspace_admin"],
            "status": "active",
            "joinedAt": now,
            "invitedBy": None,
            "lastActiveAt": now,
        })
        state.setdefault("workspaceSelections", {})[actor["accountId"]] = workspace_id
        self.store.save(state)
        result = self.directory(actor, trace_id)
        result["status"] = 201
        return result

    def switch_workspace(self, payload: dict[str, Any], actor: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        workspace_id = str(payload.get("workspaceId") or "").strip()
        if not workspace_id:
            return workspace_problem(422, "Workspace ID is required.", path, trace_id, "#/workspaceId")

        state = self.store.load()
        target_workspace = workspace(state, workspace_id)
        if not target_workspace or target_workspace.get("status") != "active":
            return workspace_problem(404, "Workspace was not found.", path, trace_id, "#/workspaceId")

        membership = current_membership(state, actor["accountId"], workspace_id)
        if not membership:
            return workspace_problem(403, "Workspace membership is required.", path, trace_id, "#/workspaceId")

        now = utc_now()
        membership["lastActiveAt"] = now
        state.setdefault("workspaceSelections", {})[actor["accountId"]] = workspace_id
        self.store.save(state)
        return self.directory(actor, trace_id)

    def admin_summary(self, actor: dict[str, Any], metrics: dict[str, Any], trace_id: str) -> dict[str, Any]:
        state = self.store.load()
        membership = current_membership(state, actor["accountId"])
        current_workspace = workspace(state, membership["workspaceId"]) if membership else None
        boundary = permission_boundary(state, actor, membership)

        if not current_workspace or current_workspace.get("status") != "active" or "view_workspace_admin" not in boundary["allowedActions"]:
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

        if selected_group_id == "workspace_owner":
            owner_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_ownership", path, trace_id)
            if owner_problem:
                return owner_problem
            missing_required = [item for item in WORKSPACE_OWNER_REQUIRED_PERMISSIONS if item not in parsed["permissions"]]
            if missing_required:
                detail = f"Workspace owner group must retain {missing_required[0]}."
                return workspace_problem(422, detail, path, trace_id, "#/permissions")

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

        if selected_group_id == "workspace_owner":
            return workspace_problem(409, "Workspace owner group cannot be deleted.", path, trace_id, "#/groupId")

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

    def update_member(
        self,
        workspace_id: str,
        membership_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_members", path, trace_id)
        if access_problem:
            return access_problem

        member = stored_membership(state, workspace_id, membership_id)
        if not member:
            return workspace_problem(404, "Workspace member was not found.", path, trace_id, "#/membershipId")

        parsed = parse_member_group_payload(state, workspace_id, payload, path, trace_id)
        if "body" in parsed:
            return parsed

        owner_changed = ("workspace_owner" in member.get("groupIds", [])) != ("workspace_owner" in parsed["groupIds"])
        if owner_changed:
            owner_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_ownership", path, trace_id)
            if owner_problem:
                return owner_problem

        if not _workspace_has_owner_after_member_change(state, workspace_id, membership_id, parsed["groupIds"]):
            return workspace_problem(409, "At least one active Workspace owner member is required.", path, trace_id, "#/groupIds")

        if not _workspace_has_admin_after_member_change(state, workspace_id, membership_id, parsed["groupIds"]):
            return workspace_problem(409, "At least one active Workspace admin member is required.", path, trace_id, "#/groupIds")

        member["groupIds"] = parsed["groupIds"]
        self.store.save(state)
        return response(200, envelope(copy.deepcopy(member), trace_id), trace_id)

    def remove_member(
        self,
        workspace_id: str,
        membership_id: str,
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_members", path, trace_id)
        if access_problem:
            return access_problem

        member = stored_membership(state, workspace_id, membership_id)
        if not member:
            return workspace_problem(404, "Workspace member was not found.", path, trace_id, "#/membershipId")

        if member["accountId"] == actor["accountId"]:
            return workspace_problem(409, "Workspace admins cannot remove their own active membership.", path, trace_id, "#/membershipId")

        if "workspace_owner" in member.get("groupIds", []):
            owner_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_ownership", path, trace_id)
            if owner_problem:
                return owner_problem

        if not _workspace_has_owner_after_member_removal(state, workspace_id, membership_id):
            return workspace_problem(409, "At least one active Workspace owner member is required.", path, trace_id, "#/membershipId")

        if not _workspace_has_admin_after_member_removal(state, workspace_id, membership_id):
            return workspace_problem(409, "At least one active Workspace admin member is required.", path, trace_id, "#/membershipId")

        now = utc_now()
        removed = copy.deepcopy(member)
        member["status"] = "removed"
        member["removedAt"] = now
        member["removedBy"] = actor["accountId"]
        selections = state.setdefault("workspaceSelections", {})
        if selections.get(member["accountId"]) == workspace_id:
            selections.pop(member["accountId"], None)
        self.store.save(state)
        return response(200, envelope({**removed, "status": "removed", "removedAt": now, "removedBy": actor["accountId"]}, trace_id), trace_id)

    def transfer_owner(
        self,
        workspace_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_ownership", path, trace_id)
        if access_problem:
            return access_problem

        membership_id = str(payload.get("membershipId") or "").strip()
        if not membership_id:
            return workspace_problem(422, "Target member is required.", path, trace_id, "#/membershipId")

        target = stored_membership(state, workspace_id, membership_id)
        if not target:
            return workspace_problem(404, "Workspace member was not found.", path, trace_id, "#/membershipId")

        now = utc_now()
        for member in state["memberships"]:
            if member["workspaceId"] != workspace_id or member["status"] != "active":
                continue
            if member["membershipId"] == membership_id:
                member["groupIds"] = list(dict.fromkeys([*member.get("groupIds", []), "workspace_owner", "workspace_admin"]))
                member["lastActiveAt"] = now
            else:
                member["groupIds"] = [group_id for group_id in member.get("groupIds", []) if group_id != "workspace_owner"]

        self.store.save(state)
        updated = stored_membership(state, workspace_id, membership_id)
        return response(200, envelope(copy.deepcopy(updated), trace_id), trace_id)

    def delete_workspace(
        self,
        workspace_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        trace_id: str,
        path: str,
    ) -> dict[str, Any]:
        state = self.store.load()
        access_problem = require_workspace_permission(state, workspace_id, actor, "manage_workspace_ownership", path, trace_id)
        if access_problem:
            return access_problem

        target_workspace = workspace(state, workspace_id)
        if not target_workspace or target_workspace.get("status") != "active":
            return workspace_problem(404, "Workspace was not found.", path, trace_id, "#/workspaceId")

        confirmation = str(payload.get("workspaceName") or "").strip()
        if confirmation != target_workspace["name"]:
            return workspace_problem(422, "Workspace name confirmation must match exactly.", path, trace_id, "#/workspaceName")

        now = utc_now()
        deleted = copy.deepcopy(target_workspace)
        target_workspace["status"] = "deleted"
        target_workspace["deletedAt"] = now
        target_workspace["deletedBy"] = actor["accountId"]

        for member in state["memberships"]:
            if member["workspaceId"] == workspace_id and member["status"] == "active":
                member["status"] = "removed"
                member["removedAt"] = now
                member["removedBy"] = actor["accountId"]
                member["removalReason"] = "workspace_deleted"

        for invitation in state["invitations"]:
            if invitation["workspaceId"] == workspace_id and invitation["status"] == "pending":
                invitation["status"] = "revoked"
                invitation["revokedAt"] = now

        selections = state.setdefault("workspaceSelections", {})
        for account_id, selected_workspace_id in list(selections.items()):
            if selected_workspace_id == workspace_id:
                selections.pop(account_id, None)

        self.store.save(state)
        return response(200, envelope({**deleted, "status": "deleted", "deletedAt": now, "deletedBy": actor["accountId"]}, trace_id), trace_id)

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
        if "workspace_owner" in unique_group_ids:
            return workspace_problem(422, "Workspace owner cannot be granted by invitation link.", path, trace_id, "#/groupIds")
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
        state.setdefault("workspaceSelections", {})[actor["accountId"]] = invitation["workspaceId"]
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


def _workspace_has_admin_after_member_change(
    state: dict[str, Any],
    workspace_id: str,
    changed_membership_id: str,
    changed_group_ids: list[str],
) -> bool:
    for member in state["memberships"]:
        if member["workspaceId"] != workspace_id or member["status"] != "active":
            continue
        group_ids = changed_group_ids if member["membershipId"] == changed_membership_id else member.get("groupIds", [])
        if "workspace_admin" in group_ids:
            return True
    return False


def _workspace_has_owner_after_member_change(
    state: dict[str, Any],
    workspace_id: str,
    changed_membership_id: str,
    changed_group_ids: list[str],
) -> bool:
    for member in state["memberships"]:
        if member["workspaceId"] != workspace_id or member["status"] != "active":
            continue
        group_ids = changed_group_ids if member["membershipId"] == changed_membership_id else member.get("groupIds", [])
        if "workspace_owner" in group_ids:
            return True
    return False


def _workspace_has_admin_after_member_removal(state: dict[str, Any], workspace_id: str, removed_membership_id: str) -> bool:
    return any(
        member["workspaceId"] == workspace_id
        and member["membershipId"] != removed_membership_id
        and member["status"] == "active"
        and "workspace_admin" in member.get("groupIds", [])
        for member in state["memberships"]
    )


def _workspace_has_owner_after_member_removal(state: dict[str, Any], workspace_id: str, removed_membership_id: str) -> bool:
    return any(
        member["workspaceId"] == workspace_id
        and member["membershipId"] != removed_membership_id
        and member["status"] == "active"
        and "workspace_owner" in member.get("groupIds", [])
        for member in state["memberships"]
    )
