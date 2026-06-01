import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.source_http import build_sqlite_app


class SourceAssignmentPermissionTests(unittest.TestCase):
    def test_assigned_source_findings_are_visible_only_to_owner_and_owner_can_change(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contacts.txt").write_text("Contact privacy.reviewer@example.org for the retention review.", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_assignment_create",
                    json.dumps({
                        "assignedOwnerUserId": "user_anna",
                        "sourceId": "source_assigned_local",
                        "name": "Assigned Local Source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_assigned_local/connect-test", "trace_assignment_connect")
                app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_assignment_scan",
                    json.dumps({"sourceId": "source_assigned_local"}),
                    "application/json",
                )
                time.sleep(1.1)
                admin_findings = app.handle("GET", "/api/findings", "trace_assignment_admin_findings")
                owner_findings = app.handle("GET", "/api/findings", "trace_assignment_owner_findings", headers={"X-Actor-Id": "user_anna"})
                auditor_findings = app.handle("GET", "/api/findings", "trace_assignment_auditor_findings", headers={"X-Actor-Id": "user_lee"})
                finding_id = owner_findings["body"]["data"][0]["findingId"]
                support = app.handle("GET", f"/api/findings/{finding_id}/review-support", "trace_assignment_support", headers={"X-Actor-Id": "user_anna"})
                transfer_ids = {item["userId"] for item in support["body"]["data"]["transferOptions"]}
                rejected_review = app.handle(
                    "POST",
                    f"/api/findings/{finding_id}/review",
                    "trace_assignment_review_rejected",
                    json.dumps({
                        "actorId": "user_anna",
                        "checklistItemIds": ["review_redacted_evidence", "confirm_business_purpose", "confirm_permission_boundary"],
                        "decision": "delete_candidate",
                        "reason": "No business purpose remains.",
                    }),
                    "application/json",
                    {"X-Actor-Id": "user_anna"},
                )
                checklist_ids = [item["itemId"] for item in support["body"]["data"]["checklist"]]
                accepted_review = app.handle(
                    "POST",
                    f"/api/findings/{finding_id}/review",
                    "trace_assignment_review_accepted",
                    json.dumps({
                        "actorId": "user_anna",
                        "checklistItemIds": checklist_ids,
                        "decision": "delete_candidate",
                        "reason": "No business purpose remains.",
                    }),
                    "application/json",
                    {"X-Actor-Id": "user_anna"},
                )
                updated = app.handle(
                    "PATCH",
                    "/api/sources/source_assigned_local",
                    "trace_assignment_update",
                    json.dumps({"assignedOwnerUserId": "user_marta"}),
                    "application/json",
                )
                previous_owner_findings = app.handle("GET", "/api/findings", "trace_assignment_previous_owner", headers={"X-Actor-Id": "user_anna"})
                steward_findings = app.handle("GET", "/api/findings", "trace_assignment_steward", headers={"X-Actor-Id": "user_marta"})

        self.assertEqual(created["status"], 201)
        self.assertEqual(created["body"]["data"]["assignedOwner"]["displayName"], "Anna Privacy Reviewer")
        self.assertEqual(admin_findings["body"]["data"], [])
        self.assertEqual(len(owner_findings["body"]["data"]), 1)
        self.assertEqual(auditor_findings["body"]["data"], [])
        self.assertIn("user_marta", transfer_ids)
        self.assertNotIn("user_markus", transfer_ids)
        self.assertEqual(rejected_review["status"], 422)
        self.assertEqual(accepted_review["status"], 201)
        self.assertFalse(accepted_review["body"]["data"]["deletionExecuted"])
        self.assertEqual(updated["status"], 200)
        self.assertEqual(updated["body"]["data"]["assignedOwner"]["displayName"], "Marta Data Steward")
        self.assertEqual(previous_owner_findings["body"]["data"], [])
        self.assertEqual(len(steward_findings["body"]["data"]), 1)


if __name__ == "__main__":
    unittest.main()
