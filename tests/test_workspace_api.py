from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.datasentinel.source_http import build_sqlite_app
from backend.datasentinel.source_server import make_handler
from backend.datasentinel.sqlite_store import SQLiteAuthStore, SQLiteDocumentStore


SESSION_COOKIE = "datasentinel_session"


def create_session(db_path: Path, user_id: str, email: str) -> str:
    store = SQLiteAuthStore(SQLiteDocumentStore(db_path))
    store.upsert_user({
        "userId": user_id,
        "provider": "github",
        "providerSubject": user_id,
        "displayName": user_id.replace("_", " ").title(),
        "email": email,
        "avatarUrl": None,
    })
    session_id = store.create_session(user_id, int(time.time()) + 600)
    return f"{SESSION_COOKIE}={session_id}"


class WorkspaceApiTests(unittest.TestCase):
    def test_new_sqlite_account_has_no_workspace_membership(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            cookie = create_session(db_path, "user_new_account", "new.account@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                directory_response = app.handle("GET", "/api/workspaces", "trace_workspace_empty", None, None, {"Cookie": cookie})
                admin_response = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_empty_admin", None, None, {"Cookie": cookie})

        self.assertEqual(directory_response["status"], 200)
        self.assertTrue(directory_response["body"]["data"]["workspaceRequired"])
        self.assertEqual(directory_response["body"]["data"]["workspaces"], [])
        self.assertIsNone(directory_response["body"]["data"]["currentWorkspaceId"])
        self.assertIsNone(admin_response["body"]["data"]["workspace"])
        self.assertIn("view_workspace_admin", {item["action"] for item in admin_response["body"]["data"]["permissionBoundary"]["deniedActions"]})

    def test_signed_in_account_can_create_workspace_as_admin(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            cookie = create_session(db_path, "user_creator", "creator@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/workspaces",
                    "trace_workspace_create",
                    json.dumps({"name": "Privacy Ops"}),
                    "application/json",
                    {"Cookie": cookie},
                )
                workspace_id = created["body"]["data"]["currentWorkspaceId"]
                summary = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_created_admin", None, None, {"Cookie": cookie})

        self.assertEqual(created["status"], 201)
        self.assertFalse(created["body"]["data"]["workspaceRequired"])
        self.assertEqual(created["body"]["data"]["workspaces"][0]["name"], "Privacy Ops")
        self.assertEqual(summary["body"]["data"]["workspace"]["workspaceId"], workspace_id)
        self.assertEqual(summary["body"]["data"]["currentMembership"]["groupIds"], ["workspace_admin"])
        self.assertIn("invite_workspace_members", summary["body"]["data"]["permissionBoundary"]["allowedActions"])

    def test_workspace_admin_can_create_invite_link_and_signed_in_account_accepts_once(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            admin_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            target_cookie = create_session(db_path, "user_candidate", "candidate@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/invitations",
                    "trace_workspace_invite",
                    json.dumps({"groupIds": ["privacy_reviewer"]}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                invitation_id = created["body"]["data"]["invitationId"]
                directory_before = app.handle("GET", "/api/workspaces", "trace_workspace_pending", None, None, {"Cookie": target_cookie})
                accepted = app.handle(
                    "POST",
                    f"/api/workspaces/invitations/{invitation_id}/accept",
                    "trace_workspace_accept",
                    "{}",
                    "application/json",
                    {"Cookie": target_cookie},
                )
                repeated = app.handle(
                    "POST",
                    f"/api/workspaces/invitations/{invitation_id}/accept",
                    "trace_workspace_accept_repeat",
                    "{}",
                    "application/json",
                    {"Cookie": target_cookie},
                )
                directory_after = app.handle("GET", "/api/workspaces", "trace_workspace_joined", None, None, {"Cookie": target_cookie})
                denied_invite = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/invitations",
                    "trace_workspace_denied_invite",
                    json.dumps({"groupIds": ["auditor"]}),
                    "application/json",
                    {"Cookie": target_cookie},
                )

        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["data"]["invitePath"], f"/workspace/invitations/{invitation_id}")
        self.assertEqual(directory_before["body"]["data"]["pendingInvitations"], [])
        self.assertEqual(accepted["status"], 200)
        self.assertFalse(accepted["body"]["data"]["workspaceRequired"])
        self.assertEqual(repeated["status"], 409)
        self.assertEqual(directory_after["body"]["data"]["currentWorkspaceId"], "ws_datasentinel_gdpr")
        self.assertEqual(denied_invite["status"], 403)

    def test_workspace_admin_summary_exposes_groups_members_and_charts(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            admin_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                summary = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_admin", None, None, {"Cookie": admin_cookie})

        data = summary["body"]["data"]
        self.assertEqual(summary["status"], 200)
        self.assertEqual(data["workspace"]["workspaceId"], "ws_datasentinel_gdpr")
        self.assertIn("invite_workspace_members", data["permissionBoundary"]["allowedActions"])
        self.assertGreaterEqual(len(data["members"]), 1)
        self.assertGreaterEqual(len(data["groups"]), 4)
        self.assertGreaterEqual(len(data["charts"]["membersByGroup"]), 4)
        self.assertIn("execute_real_deletion", {item["action"] for item in data["permissionBoundary"]["deniedActions"]})

    def test_workspace_admin_can_customize_groups_names_and_permissions(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            admin_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            target_cookie = create_session(db_path, "user_legal", "legal@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/groups",
                    "trace_workspace_group_create",
                    json.dumps({
                        "name": "Legal reviewers",
                        "description": "Review legal escalation evidence.",
                        "permissions": ["view_assigned_findings", "review_findings", "review_findings"],
                    }),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                group_id = created["body"]["data"]["groupId"]
                updated = app.handle(
                    "PATCH",
                    f"/api/workspaces/ws_datasentinel_gdpr/groups/{group_id}",
                    "trace_workspace_group_update",
                    json.dumps({
                        "name": "Legal triage",
                        "description": "Read audit evidence for legal triage.",
                        "permissions": ["view_workspace_audit"],
                    }),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                admin_guard = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr/groups/workspace_admin",
                    "trace_workspace_group_guard",
                    json.dumps({
                        "name": "Workspace admins",
                        "description": "Admin group.",
                        "permissions": ["view_workspace_admin"],
                    }),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                invitation = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/invitations",
                    "trace_workspace_group_invite",
                    json.dumps({"groupIds": [group_id]}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                invitation_id = invitation["body"]["data"]["invitationId"]
                accepted = app.handle(
                    "POST",
                    f"/api/workspaces/invitations/{invitation_id}/accept",
                    "trace_workspace_group_accept",
                    "{}",
                    "application/json",
                    {"Cookie": target_cookie},
                )
                target_summary = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_group_target", None, None, {"Cookie": target_cookie})
                deleted = app.handle(
                    "DELETE",
                    f"/api/workspaces/ws_datasentinel_gdpr/groups/{group_id}",
                    "trace_workspace_group_delete",
                    None,
                    None,
                    {"Cookie": admin_cookie},
                )
                summary_after_delete = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_group_after_delete", None, None, {"Cookie": admin_cookie})
                target_after_delete = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_group_target_after_delete", None, None, {"Cookie": target_cookie})

        self.assertEqual(created["status"], 201)
        self.assertTrue(group_id.startswith("custom_legal-reviewers"))
        self.assertEqual(created["body"]["data"]["permissions"], ["view_assigned_findings", "review_findings"])
        self.assertEqual(updated["body"]["data"]["name"], "Legal triage")
        self.assertEqual(updated["body"]["data"]["permissions"], ["view_workspace_audit"])
        self.assertEqual(admin_guard["status"], 422)
        self.assertEqual(accepted["status"], 200)
        self.assertIn("view_workspace_audit", target_summary["body"]["data"]["permissionBoundary"]["allowedActions"])
        self.assertEqual(deleted["status"], 200)
        self.assertNotIn(group_id, {group["groupId"] for group in summary_after_delete["body"]["data"]["groups"]})
        self.assertNotIn("view_workspace_audit", target_after_delete["body"]["data"]["permissionBoundary"]["allowedActions"])
        self.assertIn("manage_workspace_groups", {item["permission"] for item in summary_after_delete["body"]["data"]["availablePermissions"]})

    def test_http_handler_and_cors_allow_workspace_group_patch(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            app = build_sqlite_app(db_path)
            options = app.handle("OPTIONS", "/api/workspaces/ws_datasentinel_gdpr/groups/custom_group", "trace_options", None, None, {})

        self.assertTrue(callable(getattr(make_handler(app), "do_PATCH", None)))
        self.assertIn("PATCH", options["headers"]["Access-Control-Allow-Methods"])


if __name__ == "__main__":
    unittest.main()
