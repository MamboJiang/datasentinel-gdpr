from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.source_http import build_sqlite_app


class PrelaunchDeltaScanTests(unittest.TestCase):
    def test_delta_requires_completed_baseline_without_mutating_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contact.txt").write_text("Email privacy.delta@example.org", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                _register_local_source(app, root)
                rejected = app.handle(
                    "POST",
                    "/api/scans/delta",
                    "trace_delta_no_baseline",
                    json.dumps({"sourceId": "source_delta"}),
                    "application/json",
                )
                audit = app.handle("GET", "/api/audit/events", "trace_delta_no_baseline_audit")
                metrics = app.handle("GET", "/api/admin/metrics", "trace_delta_no_baseline_metrics")

        self.assertEqual(rejected["status"], 409)
        self.assertEqual(rejected["headers"]["Content-Type"], "application/problem+json")
        self.assertEqual(audit["body"]["data"], [])
        self.assertEqual(metrics["body"]["data"]["totalScannedFiles"], 0)

    def test_delta_processes_new_and_modified_files_against_private_baseline(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "unchanged.txt").write_text("Email unchanged.delta@example.org", encoding="utf-8")
            (root / "changed.txt").write_text("Phone +491711234567", encoding="utf-8")
            (root / "removed.txt").write_text("Name: Removed Person", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                _register_local_source(app, root)
                full_started = app.handle("POST", "/api/scans/full", "trace_delta_full", json.dumps({"sourceId": "source_delta"}), "application/json")
                full_scan = _wait_for_scan(app, full_started["body"]["data"]["scanId"], "trace_delta_full_done")

                (root / "changed.txt").write_text("Passport number: C01X00T88", encoding="utf-8")
                (root / "new.txt").write_text("Email new.delta@example.org", encoding="utf-8")
                (root / "removed.txt").unlink()

                delta_started = app.handle(
                    "POST",
                    "/api/scans/delta",
                    "trace_delta_start",
                    json.dumps({"sourceId": "source_delta", "baselineScanId": full_scan["body"]["data"]["scanId"]}),
                    "application/json",
                )
                running_delta = delta_started["body"]["data"]["deltaScan"]
                delta_scan = _wait_for_scan(app, delta_started["body"]["data"]["scanId"], "trace_delta_done")
                findings = app.handle("GET", "/api/findings", "trace_delta_findings")
                metrics = app.handle("GET", "/api/admin/metrics", "trace_delta_metrics")
                evaluation = app.handle("GET", "/api/evaluation/runs/latest", "trace_delta_eval")

                (root / "second.txt").write_text("Email second.delta@example.org", encoding="utf-8")
                second_delta_started = app.handle(
                    "POST",
                    "/api/scans/delta",
                    "trace_delta_second_start",
                    json.dumps({"sourceId": "source_delta", "baselineScanId": delta_scan["body"]["data"]["scanId"]}),
                    "application/json",
                )
                second_delta_scan = _wait_for_scan(app, second_delta_started["body"]["data"]["scanId"], "trace_delta_second_done")
                second_metrics = app.handle("GET", "/api/admin/metrics", "trace_delta_second_metrics")

        completed = delta_scan["body"]["data"]
        second_completed = second_delta_scan["body"]["data"]
        file_names = {finding["fileName"] for finding in findings["body"]["data"]}

        self.assertEqual(delta_started["status"], 202)
        self.assertEqual(running_delta["status"], "running")
        self.assertEqual(running_delta["baselineScanId"], full_scan["body"]["data"]["scanId"])
        self.assertEqual(completed["scanType"], "delta")
        self.assertEqual(completed["status"], "completed")
        self.assertIn("comparing_delta_baseline", [stage["stage"] for stage in completed["pipelineStages"]])
        self.assertEqual(completed["deltaScan"]["changedFiles"], 2)
        self.assertEqual(completed["deltaScan"]["newFiles"], 1)
        self.assertEqual(completed["deltaScan"]["modifiedFiles"], 1)
        self.assertEqual(completed["deltaScan"]["unchangedFiles"], 1)
        self.assertEqual(completed["deltaScan"]["missingFiles"], 1)
        self.assertEqual(completed["deltaScan"]["processedChangedFiles"], 2)
        self.assertFalse(completed["deltaScan"]["missingFilesTreatedAsDeleted"])
        self.assertFalse(completed["deltaScan"]["deletionExecuted"])
        self.assertEqual(file_names, {"changed.txt", "new.txt"})
        self.assertEqual(metrics["body"]["data"]["deltaProcessedChangedFiles"], 2)
        self.assertEqual(metrics["body"]["data"]["deltaCarriedForwardFindings"], 1)
        self.assertEqual(evaluation["body"]["data"]["deltaScanRulesHash"], completed["deltaScan"]["deltaFingerprint"])
        self.assertEqual(evaluation["body"]["data"]["resourceIntensity"]["modelCalls"], 0)
        self.assertEqual(second_delta_started["status"], 202)
        self.assertEqual(second_completed["deltaScan"]["changedFiles"], 1)
        self.assertEqual(second_completed["deltaScan"]["newFiles"], 1)
        self.assertEqual(second_completed["deltaScan"]["modifiedFiles"], 0)
        self.assertEqual(second_completed["deltaScan"]["unchangedFiles"], 3)
        self.assertEqual(second_completed["deltaScan"]["processedChangedFiles"], 1)
        self.assertEqual(second_metrics["body"]["data"]["deltaCarriedForwardFindings"], 3)


def _register_local_source(app: object, root: Path) -> None:
    app.handle(
        "POST",
        "/api/sources",
        "trace_delta_source",
        json.dumps({
            "sourceId": "source_delta",
            "name": "Delta source",
            "sourceType": "local_repo",
            "rootLabel": str(root),
            "config": {"rootPath": str(root)},
        }),
        "application/json",
    )
    app.handle("POST", "/api/sources/source_delta/connect-test", "trace_delta_connect")


def _wait_for_scan(app: object, scan_id: str, trace_id: str) -> dict:
    scan = {}
    for attempt in range(40):
        scan = app.handle("GET", f"/api/scans/{scan_id}", f"{trace_id}_{attempt}")
        if scan["body"]["data"].get("status") != "running":
            return scan
        time.sleep(0.25)
    return scan


if __name__ == "__main__":
    unittest.main()
