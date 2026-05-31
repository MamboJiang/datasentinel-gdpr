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
        self.assertEqual(summary["body"]["data"]["currentMembership"]["groupIds"], ["workspace_owner", "workspace_admin"])
        self.assertIn("manage_workspace_ownership", summary["body"]["data"]["permissionBoundary"]["allowedActions"])
        self.assertIn("invite_workspace_members", summary["body"]["data"]["permissionBoundary"]["allowedActions"])

    def test_workspace_switching_scopes_operational_state(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            creator_cookie = create_session(db_path, "user_workspace_owner", "owner@example.invalid")
            outsider_cookie = create_session(db_path, "user_workspace_outsider", "outsider@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true", "DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                workspace_a = app.handle(
                    "POST",
                    "/api/workspaces",
                    "trace_workspace_a",
                    json.dumps({"name": "Workspace A"}),
                    "application/json",
                    {"Cookie": creator_cookie},
                )
                workspace_a_id = workspace_a["body"]["data"]["currentWorkspaceId"]
                created_source = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_workspace_a_source",
                    json.dumps({
                        "sourceId": "source_workspace_a",
                        "name": "Workspace A Source",
                        "sourceType": "remote_file_link",
                        "rootLabel": "https://example.com/workspace-a.txt",
                        "config": {"url": "https://example.com/workspace-a.txt"},
                    }),
                    "application/json",
                    {"Cookie": creator_cookie},
                )
                workspace_b = app.handle(
                    "POST",
                    "/api/workspaces",
                    "trace_workspace_b",
                    json.dumps({"name": "Workspace B"}),
                    "application/json",
                    {"Cookie": creator_cookie},
                )
                workspace_b_sources = app.handle("GET", "/api/sources", "trace_workspace_b_sources", None, None, {"Cookie": creator_cookie})
                switched = app.handle(
                    "POST",
                    "/api/workspaces/current",
                    "trace_workspace_switch_a",
                    json.dumps({"workspaceId": workspace_a_id}),
                    "application/json",
                    {"Cookie": creator_cookie},
                )
                workspace_a_sources = app.handle("GET", "/api/sources", "trace_workspace_a_sources", None, None, {"Cookie": creator_cookie})
                rejected = app.handle(
                    "POST",
                    "/api/workspaces/current",
                    "trace_workspace_switch_denied",
                    json.dumps({"workspaceId": workspace_b["body"]["data"]["currentWorkspaceId"]}),
                    "application/json",
                    {"Cookie": outsider_cookie},
                )

        self.assertEqual(created_source["status"], 201)
        self.assertEqual(workspace_b_sources["body"]["data"], [])
        self.assertEqual(switched["status"], 200)
        self.assertEqual(switched["body"]["data"]["currentWorkspaceId"], workspace_a_id)
        self.assertIn("source_workspace_a", {source["sourceId"] for source in workspace_a_sources["body"]["data"]})
        self.assertEqual(rejected["status"], 403)

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

    def test_workspace_admin_can_customize_workspace_profile(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            admin_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            reviewer_cookie = create_session(db_path, "user_anna", "anna.reviewer@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                updated = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_profile_update",
                    json.dumps({
                        "description": "Production privacy operations",
                        "headerLabel": "Pilot",
                        "name": "Acme Privacy Ops",
                    }),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                directory_response = app.handle("GET", "/api/workspaces", "trace_workspace_profile_directory", None, None, {"Cookie": admin_cookie})
                hidden = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_header_hide",
                    json.dumps({"headerLabel": "   "}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                denied = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_header_denied",
                    json.dumps({"headerLabel": "Reviewer"}),
                    "application/json",
                    {"Cookie": reviewer_cookie},
                )
                too_long = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_header_long",
                    json.dumps({"headerLabel": "This label is definitely too long"}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )

        self.assertEqual(updated["status"], 200)
        self.assertEqual(updated["body"]["data"]["name"], "Acme Privacy Ops")
        self.assertEqual(updated["body"]["data"]["slug"], "acme-privacy-ops")
        self.assertEqual(updated["body"]["data"]["description"], "Production privacy operations")
        self.assertEqual(updated["body"]["data"]["headerLabel"], "Pilot")
        self.assertEqual(directory_response["body"]["data"]["workspaces"][0]["name"], "Acme Privacy Ops")
        self.assertEqual(directory_response["body"]["data"]["workspaces"][0]["description"], "Production privacy operations")
        self.assertEqual(directory_response["body"]["data"]["workspaces"][0]["headerLabel"], "Pilot")
        self.assertEqual(hidden["body"]["data"]["headerLabel"], "")
        self.assertEqual(hidden["body"]["data"]["name"], "Acme Privacy Ops")
        self.assertEqual(denied["status"], 403)
        self.assertEqual(too_long["status"], 422)

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

    def test_workspace_admin_can_update_and_remove_members(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            admin_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            target_cookie = create_session(db_path, "user_managed", "managed@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                invitation = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/invitations",
                    "trace_workspace_member_invite",
                    json.dumps({"groupIds": ["privacy_reviewer"]}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                invitation_id = invitation["body"]["data"]["invitationId"]
                app.handle(
                    "POST",
                    f"/api/workspaces/invitations/{invitation_id}/accept",
                    "trace_workspace_member_accept",
                    "{}",
                    "application/json",
                    {"Cookie": target_cookie},
                )
                membership_id = "mem_user_managed_ws_datasentinel_gdpr"
                updated = app.handle(
                    "PATCH",
                    f"/api/workspaces/ws_datasentinel_gdpr/members/{membership_id}",
                    "trace_workspace_member_update",
                    json.dumps({"groupIds": ["auditor", "auditor"]}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                target_summary = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_member_target_summary", None, None, {"Cookie": target_cookie})
                denied_update = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr/members/mem_demo_admin",
                    "trace_workspace_member_denied_update",
                    json.dumps({"groupIds": ["auditor"]}),
                    "application/json",
                    {"Cookie": target_cookie},
                )
                last_admin_guard = app.handle(
                    "PATCH",
                    "/api/workspaces/ws_datasentinel_gdpr/members/mem_demo_admin",
                    "trace_workspace_member_last_admin_guard",
                    json.dumps({"groupIds": ["auditor"]}),
                    "application/json",
                    {"Cookie": admin_cookie},
                )
                removed = app.handle(
                    "DELETE",
                    f"/api/workspaces/ws_datasentinel_gdpr/members/{membership_id}",
                    "trace_workspace_member_remove",
                    None,
                    None,
                    {"Cookie": admin_cookie},
                )
                summary_after_remove = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_member_after_remove", None, None, {"Cookie": admin_cookie})
                self_remove = app.handle(
                    "DELETE",
                    "/api/workspaces/ws_datasentinel_gdpr/members/mem_demo_admin",
                    "trace_workspace_member_self_remove",
                    None,
                    None,
                    {"Cookie": admin_cookie},
                )

        self.assertEqual(updated["status"], 200)
        self.assertEqual(updated["body"]["data"]["groupIds"], ["auditor"])
        self.assertIn("view_workspace_audit", target_summary["body"]["data"]["permissionBoundary"]["allowedActions"])
        self.assertEqual(denied_update["status"], 403)
        self.assertEqual(last_admin_guard["status"], 409)
        self.assertEqual(removed["status"], 200)
        self.assertEqual(removed["body"]["data"]["status"], "removed")
        self.assertNotIn(membership_id, {member["membershipId"] for member in summary_after_remove["body"]["data"]["members"]})
        self.assertEqual(self_remove["status"], 409)

    def test_workspace_owner_can_transfer_owner_and_delete_workspace_with_name_confirmation(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            owner_cookie = create_session(db_path, "user_demo_admin", "demo.admin@example.invalid")
            target_cookie = create_session(db_path, "user_owner_target", "owner.target@example.invalid")
            with mock.patch.dict("os.environ", {"DATASENTINEL_AUTH_REQUIRED": "true"}):
                app = build_sqlite_app(db_path)
                invitation = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/invitations",
                    "trace_workspace_owner_invite",
                    json.dumps({"groupIds": ["privacy_reviewer"]}),
                    "application/json",
                    {"Cookie": owner_cookie},
                )
                invitation_id = invitation["body"]["data"]["invitationId"]
                app.handle(
                    "POST",
                    f"/api/workspaces/invitations/{invitation_id}/accept",
                    "trace_workspace_owner_accept",
                    "{}",
                    "application/json",
                    {"Cookie": target_cookie},
                )
                target_membership_id = "mem_user_owner_target_ws_datasentinel_gdpr"
                transferred = app.handle(
                    "POST",
                    "/api/workspaces/ws_datasentinel_gdpr/owner-transfer",
                    "trace_workspace_owner_transfer",
                    json.dumps({"membershipId": target_membership_id}),
                    "application/json",
                    {"Cookie": owner_cookie},
                )
                prior_owner_summary = app.handle("GET", "/api/workspaces/current/admin", "trace_workspace_prior_owner", None, None, {"Cookie": owner_cookie})
                prior_owner_delete = app.handle(
                    "DELETE",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_prior_owner_delete",
                    json.dumps({"workspaceName": "DataSentinel GDPR"}),
                    "application/json",
                    {"Cookie": owner_cookie},
                )
                wrong_name_delete = app.handle(
                    "DELETE",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_wrong_name_delete",
                    json.dumps({"workspaceName": "datasentinel gdpr"}),
                    "application/json",
                    {"Cookie": target_cookie},
                )
                deleted = app.handle(
                    "DELETE",
                    "/api/workspaces/ws_datasentinel_gdpr",
                    "trace_workspace_delete",
                    json.dumps({"workspaceName": "DataSentinel GDPR"}),
                    "application/json",
                    {"Cookie": target_cookie},
                )
                directory_after_delete = app.handle("GET", "/api/workspaces", "trace_workspace_delete_directory", None, None, {"Cookie": target_cookie})

        self.assertEqual(transferred["status"], 200)
        self.assertEqual(transferred["body"]["data"]["groupIds"], ["privacy_reviewer", "workspace_owner", "workspace_admin"])
        self.assertNotIn("manage_workspace_ownership", prior_owner_summary["body"]["data"]["permissionBoundary"]["allowedActions"])
        self.assertEqual(prior_owner_delete["status"], 403)
        self.assertEqual(wrong_name_delete["status"], 422)
        self.assertEqual(deleted["status"], 200)
        self.assertEqual(deleted["body"]["data"]["status"], "deleted")
        self.assertTrue(directory_after_delete["body"]["data"]["workspaceRequired"])
        self.assertEqual(directory_after_delete["body"]["data"]["workspaces"], [])

    def test_http_handler_and_cors_allow_workspace_group_patch(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            app = build_sqlite_app(db_path)
            options = app.handle("OPTIONS", "/api/workspaces/ws_datasentinel_gdpr/groups/custom_group", "trace_options", None, None, {})

        self.assertTrue(callable(getattr(make_handler(app), "do_PATCH", None)))
        self.assertIn("PATCH", options["headers"]["Access-Control-Allow-Methods"])


if __name__ == "__main__":
    unittest.main()
