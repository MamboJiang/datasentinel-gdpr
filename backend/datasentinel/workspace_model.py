"""Read-model helpers for Workspace membership and permissions."""

from __future__ import annotations

import copy
import hashlib
from datetime import UTC, datetime
from typing import Any

from .envelope import utc_now
from .workspace_seed import WORKSPACE_PERMISSION_OPTIONS

REAL_DELETION_DENIAL = {"action": "execute_real_deletion", "reason": "Real deletion is disabled in P0."}


def account_payload(actor: dict[str, Any]) -> dict[str, Any]:
    return {"accountId": actor["accountId"], "displayName": actor["displayName"], "email": actor.get("email")}


def workspace(state: dict[str, Any], workspace_id: str) -> dict[str, Any] | None:
    return next((item for item in state["workspaces"] if item["workspaceId"] == workspace_id), None)


def workspace_summary(state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    workspace_id = item["workspaceId"]
    members = memberships(state, workspace_id)
    invitations = [candidate for candidate in state["invitations"] if candidate["workspaceId"] == workspace_id and candidate["status"] == "pending"]
    return {**copy.deepcopy(item), "memberCount": len(members), "pendingInvitationCount": len(invitations)}


def groups(state: dict[str, Any], workspace_id: str) -> list[dict[str, Any]]:
    members = memberships(state, workspace_id)
    result = []
    for group in state["groups"]:
        if group["workspaceId"] != workspace_id:
            continue
        group_id = group["groupId"]
        result.append({**copy.deepcopy(group), "memberCount": sum(group_id in member["groupIds"] for member in members)})
    return result


def memberships(state: dict[str, Any], workspace_id: str) -> list[dict[str, Any]]:
    return [copy.deepcopy(item) for item in state["memberships"] if item["workspaceId"] == workspace_id and item["status"] == "active"]


def active_memberships(state: dict[str, Any], account_id: str) -> list[dict[str, Any]]:
    return [item for item in state["memberships"] if item["accountId"] == account_id and item["status"] == "active"]


def current_membership(state: dict[str, Any], account_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
    available = active_memberships(state, account_id)
    if workspace_id:
        return next((item for item in available if item["workspaceId"] == workspace_id), None)
    return available[-1] if available else None


def matching_pending_invitations(state: dict[str, Any], actor: dict[str, Any]) -> list[dict[str, Any]]:
    email = str(actor.get("email") or "").lower()
    if not email:
        return []
    return [
        copy.deepcopy(item) for item in state["invitations"]
        if item["status"] == "pending" and str(item.get("email") or "").lower() == email
    ]


def permission_boundary(state: dict[str, Any], actor: dict[str, Any], membership: dict[str, Any] | None) -> dict[str, Any]:
    if not membership:
        allowed: list[str] = []
        roles: list[str] = []
        workspace_id = None
        denied = [{"action": "view_workspace_admin", "reason": "Account is not a member of a Workspace."}, REAL_DELETION_DENIAL]
    else:
        workspace_id = membership["workspaceId"]
        roles = membership["groupIds"]
        group_permissions = [group["permissions"] for group in groups(state, workspace_id) if group["groupId"] in roles]
        allowed = sorted({permission for permissions in group_permissions for permission in permissions})
        denied = _denials_for_allowed(allowed)

    fingerprint = hashlib.sha256(f"{actor['accountId']}:{workspace_id}:{','.join(roles)}:{','.join(allowed)}".encode("utf-8")).hexdigest()[:24]
    return {
        "actorId": actor["accountId"],
        "workspaceId": workspace_id,
        "roles": roles,
        "allowedActions": allowed,
        "deniedActions": denied,
        "visibleScopes": [f"workspace:{workspace_id}"] if workspace_id else [],
        "boundaryFingerprint": f"sha256:{fingerprint}",
        "evaluatedAt": utc_now(),
    }


def empty_admin_summary(actor: dict[str, Any], item: dict[str, Any] | None, membership: dict[str, Any] | None, boundary: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace": copy.deepcopy(item) if item else None,
        "currentMembership": copy.deepcopy(membership) if membership else None,
        "permissionBoundary": boundary,
        "availablePermissions": copy.deepcopy(WORKSPACE_PERMISSION_OPTIONS),
        "groups": [],
        "members": [],
        "invitations": [],
        "charts": {"membersByGroup": [], "invitationStatus": [], "reviewLoad": [], "riskOverview": [], "scanCoverage": []},
        "account": account_payload(actor),
    }


def charts(workspace_groups: list[dict[str, Any]], invitations: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    pending = sum(item["status"] == "pending" for item in invitations)
    accepted = sum(item["status"] == "accepted" for item in invitations)
    expired = sum(item["status"] == "expired" for item in invitations)
    return {
        "membersByGroup": [{"label": group["name"], "value": group["memberCount"], "tone": _tone(group["groupId"])} for group in workspace_groups],
        "invitationStatus": [
            {"label": "Pending", "value": pending, "tone": "yellow"},
            {"label": "Accepted", "value": accepted, "tone": "green"},
            {"label": "Expired", "value": expired, "tone": "neutral"},
        ],
        "reviewLoad": [
            {"label": "Open backlog", "value": metrics.get("openReviewBacklog", 0), "tone": "blue"},
            {"label": "High risk", "value": metrics.get("highRiskFindings", 0), "tone": "red"},
            {"label": "Review decisions", "value": metrics.get("reviewDecisionCount", 0), "tone": "green"},
        ],
        "riskOverview": [
            {"label": "Flagged files", "value": metrics.get("flaggedFiles", 0), "tone": "blue"},
            {"label": "Retention review", "value": metrics.get("retentionOverdueFiles", 0), "tone": "yellow"},
            {"label": "False positives", "value": metrics.get("falsePositiveDecisions", 0), "tone": "neutral"},
        ],
        "scanCoverage": [
            {"label": "Scanned files", "value": metrics.get("totalScannedFiles", 0), "tone": "black"},
            {"label": "Fingerprint records", "value": metrics.get("fingerprintedFiles", metrics.get("totalScannedFiles", 0)), "tone": "green"},
            {"label": "Extraction warnings", "value": metrics.get("extractionWarnings", 0), "tone": "yellow"},
        ],
    }


def expired(expires_at: str) -> bool:
    try:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return parsed <= datetime.now(UTC)


def _denials_for_allowed(allowed: list[str]) -> list[dict[str, str]]:
    denials = [REAL_DELETION_DENIAL, {"action": "sync_enterprise_directory", "reason": "Production directory and tenant sync are out of scope for P0."}]
    if "view_workspace_admin" not in allowed:
        denials.insert(0, {"action": "view_workspace_admin", "reason": "Workspace admin view permission is required."})
    if "invite_workspace_members" not in allowed:
        denials.insert(0, {"action": "invite_workspace_members", "reason": "Workspace admin group is required."})
    if "manage_workspace_members" not in allowed:
        denials.insert(0, {"action": "manage_workspace_members", "reason": "Workspace admin group is required."})
    if "manage_workspace_groups" not in allowed:
        denials.insert(0, {"action": "manage_workspace_groups", "reason": "Workspace group management permission is required."})
    return denials


def _tone(group_id: str) -> str:
    return {"workspace_admin": "black", "privacy_reviewer": "blue", "data_steward": "green", "auditor": "neutral"}.get(group_id, "neutral")
