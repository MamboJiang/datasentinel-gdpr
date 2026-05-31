import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.datasentinel.source_http import build_sqlite_app


class PrelaunchSourceDeletionTests(unittest.TestCase):
    def test_empty_prelaunch_metrics_do_not_emit_partial_aggregation(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                metrics = app.handle("GET", "/api/admin/metrics", "trace_empty_metrics")

            self.assertEqual(metrics["status"], 200)
            self.assertEqual(metrics["body"]["data"]["flaggedFiles"], 0)
            self.assertNotIn("aggregation", metrics["body"]["data"])

    def test_deleting_current_source_clears_derived_workflow_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contacts.txt").write_text("Contact privacy.reviewer@example.org for this record.", encoding="utf-8")
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_delete_current_create",
                    json.dumps({
                        "sourceId": "source_local_delete",
                        "name": "Delete Current Source",
                        "sourceType": "local_repo",
                        "status": "registered",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                connected = app.handle("POST", "/api/sources/source_local_delete/connect-test", "trace_delete_current_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_delete_current_scan",
                    json.dumps({"sourceId": "source_local_delete"}),
                    "application/json",
                )
                time.sleep(1.1)
                completed = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_delete_current_completed")
                findings_before_delete = app.handle("GET", "/api/findings", "trace_delete_current_findings_before")
                deleted = app.handle("DELETE", "/api/sources/source_local_delete", "trace_delete_current_delete")
                sources_after_delete = app.handle("GET", "/api/sources", "trace_delete_current_sources_after")
                scan_after_delete = app.handle("GET", "/api/scans/current", "trace_delete_current_scan_after")
                findings_after_delete = app.handle("GET", "/api/findings", "trace_delete_current_findings_after")
                metrics_after_delete = app.handle("GET", "/api/admin/metrics", "trace_delete_current_metrics_after")

                restarted = build_sqlite_app(db_path, [root])
                restarted_scan = restarted.handle("GET", "/api/scans/current", "trace_delete_current_restarted_scan")
                restarted_findings = restarted.handle("GET", "/api/findings", "trace_delete_current_restarted_findings")

            self.assertEqual(created["status"], 201)
            self.assertEqual(connected["body"]["data"]["connectionStatus"], "connected")
            self.assertEqual(completed["body"]["data"]["status"], "completed")
            self.assertEqual(len(findings_before_delete["body"]["data"]), 1)
            self.assertEqual(deleted["status"], 200)
            self.assertEqual(sources_after_delete["body"]["data"], [])
            self.assertEqual(scan_after_delete["body"]["data"]["status"], "idle")
            self.assertEqual(scan_after_delete["body"]["data"]["sourceId"], "")
            self.assertEqual(findings_after_delete["body"]["data"], [])
            self.assertNotIn("aggregation", metrics_after_delete["body"]["data"])
            self.assertEqual(restarted_scan["body"]["data"]["status"], "idle")
            self.assertEqual(restarted_findings["body"]["data"], [])


if __name__ == "__main__":
    unittest.main()
