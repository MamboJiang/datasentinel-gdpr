"""Seed data for the local Workspace P0 state."""

from __future__ import annotations

from typing import Any

DEFAULT_WORKSPACE_ID = "ws_datasentinel_gdpr"
WORKSPACE_STATE_VERSION = "workspace-state-v1"
WORKSPACE_PERMISSION_OPTIONS = [
    {
        "permission": "manage_workspace_ownership",
        "label": "Manage Workspace owner",
        "description": "Transfer the Workspace owner role and delete the Workspace control-plane record.",
    },
    {
        "permission": "view_workspace_admin",
        "label": "View Workspace admin",
        "description": "Open the Workspace administration surface and inspect visible control-plane state.",
    },
    {
        "permission": "invite_workspace_members",
        "label": "Generate invite links",
        "description": "Create pending invitation links with explicit Workspace group assignment.",
    },
    {
        "permission": "manage_workspace_members",
        "label": "Manage members",
        "description": "Change Workspace member control-plane state when member editing is exposed.",
    },
    {
        "permission": "manage_workspace_groups",
        "label": "Manage groups",
        "description": "Create, edit, and delete Workspace groups and their permission sets.",
    },
    {
        "permission": "view_workspace_metrics",
        "label": "View metrics",
        "description": "Read Workspace-level metrics and admin charts.",
    },
    {
        "permission": "view_workspace_audit",
        "label": "View audit",
        "description": "Read Workspace audit and operational evidence.",
    },
    {
        "permission": "view_governance",
        "label": "View governance",
        "description": "Read policy-pack and governance configuration state.",
    },
    {
        "permission": "view_assigned_findings",
        "label": "View assigned findings",
        "description": "Read findings assigned or delegated to the actor.",
    },
    {
        "permission": "view_review_support",
        "label": "View review support",
        "description": "Read permission-aware reviewer guidance for findings.",
    },
    {
        "permission": "review_findings",
        "label": "Review findings",
        "description": "Record supported human review decisions inside the visible permission boundary.",
    },
    {
        "permission": "view_owned_sources",
        "label": "View owned sources",
        "description": "Read source records owned or stewarded by the actor.",
    },
]
WORKSPACE_PERMISSION_IDS = tuple(item["permission"] for item in WORKSPACE_PERMISSION_OPTIONS)
WORKSPACE_OWNER_REQUIRED_PERMISSIONS = ("manage_workspace_ownership", "view_workspace_admin", "manage_workspace_members")
WORKSPACE_ADMIN_REQUIRED_PERMISSIONS = ("view_workspace_admin", "manage_workspace_groups")


def seed_state() -> dict[str, Any]:
    return {
        "stateStoreVersion": WORKSPACE_STATE_VERSION,
        "workspaces": [{
            "workspaceId": DEFAULT_WORKSPACE_ID,
            "name": "DataSentinel GDPR",
            "slug": "datasentinel-gdpr",
            "status": "active",
            "plan": "Prelaunch",
            "description": "Privacy operations workspace",
            "createdAt": "2026-05-30T12:00:00Z",
        }],
        "groups": _seed_groups(),
        "memberships": _seed_memberships(),
        "invitations": _seed_invitations(),
        "workspaceSelections": {
            "user_demo_admin": DEFAULT_WORKSPACE_ID,
            "user_anna": DEFAULT_WORKSPACE_ID,
            "user_marta": DEFAULT_WORKSPACE_ID,
            "user_lee": DEFAULT_WORKSPACE_ID,
        },
    }


def _seed_groups() -> list[dict[str, Any]]:
    return [
        _group("workspace_owner", "Workspace owners", "Highest Workspace authority for owner transfer and Workspace deletion.", [
            "manage_workspace_ownership", "view_workspace_admin", "invite_workspace_members", "manage_workspace_members",
            "manage_workspace_groups", "view_workspace_metrics", "view_workspace_audit", "view_governance",
            "view_assigned_findings", "view_review_support", "review_findings", "view_owned_sources",
        ]),
        _group("workspace_admin", "Workspace admins", "Manage Workspace members, groups, invitations, audit, governance, and metrics.", [
            "view_workspace_admin", "invite_workspace_members", "manage_workspace_members", "manage_workspace_groups",
            "view_workspace_metrics", "view_workspace_audit", "view_governance", "view_assigned_findings",
            "view_review_support", "review_findings", "view_owned_sources",
        ]),
        _group("privacy_reviewer", "Privacy reviewers", "Review assigned findings with visible permission boundaries.", [
            "view_assigned_findings", "view_review_support", "review_findings",
        ]),
        _group("data_steward", "Data stewards", "Steward owned sources and delegated findings.", [
            "view_owned_sources", "view_assigned_findings", "review_findings",
        ]),
        _group("auditor", "Auditors", "Inspect governance, audit, and evaluation evidence without mutating workflow state.", [
            "view_workspace_audit", "view_workspace_metrics", "view_governance",
        ]),
    ]


def _group(group_id: str, name: str, description: str, permissions: list[str]) -> dict[str, Any]:
    return {"workspaceId": DEFAULT_WORKSPACE_ID, "groupId": group_id, "name": name, "description": description, "permissions": permissions}


def groups_for_workspace(workspace_id: str) -> list[dict[str, Any]]:
    return [{**group, "workspaceId": workspace_id} for group in _seed_groups()]


def _seed_memberships() -> list[dict[str, Any]]:
    return [
        _member("mem_demo_admin", "user_demo_admin", "Demo Workspace Admin", "demo.admin@example.invalid", ["workspace_owner", "workspace_admin"], None, "2026-05-30T12:20:00Z"),
        _member("mem_anna_reviewer", "user_anna", "Anna Privacy Reviewer", "anna.reviewer@example.invalid", ["privacy_reviewer"], "user_demo_admin", "2026-05-30T12:19:00Z"),
        _member("mem_marta_steward", "user_marta", "Marta Data Steward", "marta.steward@example.invalid", ["data_steward"], "user_demo_admin", "2026-05-30T12:12:00Z"),
        _member("mem_lee_auditor", "user_lee", "Lee Audit Observer", "lee.audit@example.invalid", ["auditor"], "user_demo_admin", "2026-05-30T12:10:00Z"),
    ]


def _member(membership_id: str, account_id: str, display_name: str, email: str, groups: list[str], invited_by: str | None, last_active: str) -> dict[str, Any]:
    return {
        "membershipId": membership_id,
        "workspaceId": DEFAULT_WORKSPACE_ID,
        "accountId": account_id,
        "displayName": display_name,
        "email": email,
        "groupIds": groups,
        "status": "active",
        "joinedAt": "2026-05-30T12:00:00Z",
        "invitedBy": invited_by,
        "lastActiveAt": last_active,
    }


def _seed_invitations() -> list[dict[str, Any]]:
    return [
        _invitation("invite_priya_reviewer", ["privacy_reviewer"], "2026-05-30T12:15:00Z", "2026-06-06T12:15:00Z"),
        _invitation("invite_dpo_auditor", ["auditor"], "2026-05-30T12:17:00Z", "2026-06-06T12:17:00Z"),
    ]


def _invitation(invitation_id: str, groups: list[str], created_at: str, expires_at: str) -> dict[str, Any]:
    return {
        "invitationId": invitation_id,
        "workspaceId": DEFAULT_WORKSPACE_ID,
        "invitePath": f"/workspace/invitations/{invitation_id}",
        "groupIds": groups,
        "status": "pending",
        "invitedBy": "user_demo_admin",
        "invitedByDisplayName": "Demo Workspace Admin",
        "createdAt": created_at,
        "expiresAt": expires_at,
        "acceptedAt": None,
    }
