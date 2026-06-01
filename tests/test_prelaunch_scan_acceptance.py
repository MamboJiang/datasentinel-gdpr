from __future__ import annotations

import json
from pathlib import Path
import time
import unittest
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.source_documents import SourceDocument, SourceDocumentBatch
from backend.lawdit.source_http import build_sqlite_app


class PrelaunchScanAcceptanceTests(unittest.TestCase):
    def test_scan_start_returns_before_source_documents_are_read(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contacts.txt").write_text("placeholder", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            def slow_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                time.sleep(0.35)
                return SourceDocumentBatch(
                    documents=[SourceDocument("contacts.txt", str(root / "contacts.txt"), "Contact privacy.reviewer@example.org", 36, "Local")],
                    total_files=1,
                    total_bytes=36,
                    unsupported_files=0,
                    warnings=[],
                    family="Local",
                    extraction_method="plain_text",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_acceptance_source_create",
                    json.dumps({
                        "sourceId": "source_slow_acceptance",
                        "name": "Slow acceptance source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_slow_acceptance/connect-test", "trace_acceptance_connect")

                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", slow_reader):
                    started_at = time.monotonic()
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_acceptance_scan",
                        json.dumps({"sourceId": "source_slow_acceptance"}),
                        "application/json",
                    )
                    elapsed = time.monotonic() - started_at

                    time.sleep(1.1)
                    scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_acceptance_scan_done")
                    findings = app.handle("GET", "/api/findings", "trace_acceptance_findings")

        self.assertEqual(started["status"], 202)
        self.assertEqual(started["body"]["data"]["status"], "running")
        self.assertLess(elapsed, 0.2)
        self.assertEqual(scan["body"]["data"]["status"], "completed")
        self.assertEqual(len(findings["body"]["data"]), 1)


if __name__ == "__main__":
    unittest.main()
