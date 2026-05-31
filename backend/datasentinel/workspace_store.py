"""Persistence adapters for Workspace state."""

from __future__ import annotations

import copy
from typing import Any, Protocol

from .sqlite_store import OWNER_GLOBAL, SQLiteDocumentStore
from .workspace_seed import WORKSPACE_PERMISSION_IDS, WORKSPACE_STATE_VERSION, seed_state

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
    for invitation in state.get("invitations", []):
        if not invitation.get("invitePath") and invitation.get("invitationId"):
            invitation["invitePath"] = f"/workspace/invitations/{invitation['invitationId']}"
            changed = True
    return state, changed
