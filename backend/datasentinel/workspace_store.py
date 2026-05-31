"""Persistence adapters for Workspace state."""

from __future__ import annotations

import copy
from typing import Any, Protocol

from .sqlite_store import OWNER_GLOBAL, SQLiteDocumentStore
from .workspace_seed import WORKSPACE_PERMISSION_IDS, WORKSPACE_STATE_VERSION, groups_for_workspace, seed_state

WORKSPACE_STATE_KEY = "workspace_state"


class WorkspaceStore(Protocol):
    def load(self) -> dict[str, Any]:
        """Return the persisted Workspace state document."""

    def save(self, payload: dict[str, Any]) -> None:
        """Persist the Workspace state document."""


class InMemoryWorkspaceStore:
    def __init__(self) -> None:
        self.state = seed_state()

    def load(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def save(self, payload: dict[str, Any]) -> None:
        self.state = copy.deepcopy(payload)


class SQLiteWorkspaceStore:
    def __init__(self, documents: SQLiteDocumentStore) -> None:
        self.documents = documents

    def load(self) -> dict[str, Any]:
        state = self.documents.get_workflow_document(WORKSPACE_STATE_KEY, OWNER_GLOBAL)
        if state and state.get("stateStoreVersion") == WORKSPACE_STATE_VERSION:
            state, changed = normalize_workspace_state(state)
            if changed:
                self.save(state)
            return state

        state = seed_state()
        self.save(state)
        return state

    def save(self, payload: dict[str, Any]) -> None:
        self.documents.put_workflow_document(WORKSPACE_STATE_KEY, payload, OWNER_GLOBAL)


def normalize_workspace_state(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False
    valid_permission_ids = set(WORKSPACE_PERMISSION_IDS)
    selections = state.get("workspaceSelections")
    if not isinstance(selections, dict):
        state["workspaceSelections"] = {}
        changed = True
    for group in state.get("groups", []):
        if not isinstance(group.get("description"), str):
            group["description"] = ""
            changed = True
        if not isinstance(group.get("permissions"), list):
            group["permissions"] = []
            changed = True
        filtered_permissions = [
            item for item in group["permissions"]
            if isinstance(item, str) and item in valid_permission_ids
        ]
        normalized_permissions = list(dict.fromkeys(filtered_permissions))
        if normalized_permissions != group["permissions"]:
            group["permissions"] = normalized_permissions
            changed = True
    for item in state.get("workspaces", []):
        workspace_id = item.get("workspaceId")
        if not isinstance(workspace_id, str) or not workspace_id:
            continue
        existing_group_ids = {
            group.get("groupId") for group in state.get("groups", [])
            if group.get("workspaceId") == workspace_id
        }
        missing_groups = [
            group for group in groups_for_workspace(workspace_id)
            if group["groupId"] not in existing_group_ids
        ]
        if missing_groups:
            state.setdefault("groups", []).extend(missing_groups)
            changed = True
        active_members = [
            member for member in state.get("memberships", [])
            if member.get("workspaceId") == workspace_id and member.get("status") == "active"
        ]
        has_owner = any("workspace_owner" in member.get("groupIds", []) for member in active_members)
        if not has_owner and active_members:
            owner = next((member for member in active_members if "workspace_admin" in member.get("groupIds", [])), active_members[0])
            group_ids = list(dict.fromkeys([*owner.get("groupIds", []), "workspace_owner", "workspace_admin"]))
            if group_ids != owner.get("groupIds", []):
                owner["groupIds"] = group_ids
                changed = True
    for invitation in state.get("invitations", []):
        if not invitation.get("invitePath") and invitation.get("invitationId"):
            invitation["invitePath"] = f"/workspace/invitations/{invitation['invitationId']}"
            changed = True
    return state, changed
