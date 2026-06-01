from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.datasentinel.source_http import build_sqlite_app


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"


class GoogleWorkspaceExportTests(unittest.TestCase):
    def test_drive_workspace_exports_report_real_formats_and_redacted_anchors(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            fake_client = _FakeDriveClientFactory()

            with mock.patch.dict("os.environ", {
                "DATASENTINEL_ENABLE_DEMO_FIXTURES": "false",
                "GOOGLE_CLIENT_ID": "google-client-id",
                "GOOGLE_PICKER_API_KEY": "picker-public-key",
                "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
            }), mock.patch("backend.datasentinel.source_documents.DriveFileClient", fake_client):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_workspace_export_create",
                    json.dumps({
                        "sourceId": "source_workspace_exports",
                        "name": "Workspace exports",
                        "sourceType": "google_drive_selection",
                        "rootLabel": "Selected Workspace files",
                        "config": {"items": [{"id": "workspace-folder", "name": "Workspace folder", "mimeType": "application/vnd.google-apps.folder"}]},
                    }),
                    "application/json",
                )
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_workspace_export_scan",
                    json.dumps({"sourceId": "source_workspace_exports", "authorization": {"googleDriveAccessToken": "drive-token"}}),
                    "application/json",
                )
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_workspace_export_done")
                findings = app.handle("GET", "/api/findings", "trace_workspace_export_findings")
                details = [
                    app.handle("GET", f"/api/findings/{finding['findingId']}", f"trace_workspace_export_detail_{index}")
                    for index, finding in enumerate(findings["body"]["data"])
                ]

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {(item["format"], item["method"]) for item in extraction["formatCounts"]}
        methods = {item["method"] for item in extraction["methods"]}
        signals = [
            signal
            for detail in details
            for signal in detail["body"]["data"]["signals"]
        ]
        anchor_formats = {
            signal["evidenceAnchor"]["format"]
            for signal in signals
            if isinstance(signal.get("evidenceAnchor"), dict)
        }
        selector_types = {
            signal["evidenceAnchor"]["selector"]["type"]
            for signal in signals
            if isinstance(signal.get("evidenceAnchor"), dict)
        }
        serialized = json.dumps({"scan": scan["body"], "details": [detail["body"] for detail in details]}, ensure_ascii=False)

        self.assertEqual(created["status"], 201)
        self.assertEqual(started["status"], 202)
        self.assertEqual(extraction["successfulFiles"], 3)
        self.assertEqual(extraction["unsupportedFiles"], 0)
        self.assertEqual(extraction["modelCalls"], 0)
        self.assertIn(("google_docs_export", "google_docs_plain_text_export"), formats)
        self.assertIn(("google_sheets_export", "google_sheets_csv_export"), formats)
        self.assertIn(("google_slides_export", "google_slides_plain_text_export"), formats)
        self.assertTrue({"google_docs_plain_text_export", "google_sheets_csv_export", "google_slides_plain_text_export"}.issubset(methods))
        self.assertTrue({"google_docs_export", "google_sheets_export", "google_slides_export"}.issubset(anchor_formats))
        self.assertIn("tableCell", selector_types)
        self.assertIn("textPosition", selector_types)
        self.assertEqual(fake_client.export_calls, [
            ("doc-id", "text/plain"),
            ("sheet-id", "text/csv"),
            ("slides-id", "text/plain"),
        ])
        for raw_value in (
            "Sophie de Vries",
            "docs.export@example.org",
            "Lukas Weber",
            "EN1234567",
            "+491711234567",
        ):
            self.assertNotIn(raw_value, serialized)


class _FakeDriveClientFactory:
    def __init__(self) -> None:
        self.export_calls: list[tuple[str, str]] = []

    def __call__(self, access_token: str, max_files: int, max_bytes: int) -> "_FakeDriveClient":
        self.access_token = access_token
        self.max_files = max_files
        self.max_bytes = max_bytes
        return _FakeDriveClient(self)


class _FakeDriveClient:
    def __init__(self, factory: _FakeDriveClientFactory) -> None:
        self.factory = factory

    def iter_item(self, file_id: str) -> list[dict[str, str]]:
        self.assert_folder_id(file_id)
        return [
            {"id": "doc-id", "name": "Customer intake", "mimeType": GOOGLE_DOC_MIME, "webViewLink": "https://docs.google.example/doc-id"},
            {"id": "sheet-id", "name": "Travel register", "mimeType": GOOGLE_SHEET_MIME, "webViewLink": "https://docs.google.example/sheet-id"},
            {"id": "slides-id", "name": "Briefing deck", "mimeType": GOOGLE_SLIDES_MIME, "webViewLink": "https://docs.google.example/slides-id"},
        ]

    def export(self, file_id: str, mime_type: str) -> bytes:
        self.factory.export_calls.append((file_id, mime_type))
        bodies = {
            "doc-id": "Name: Sophie de Vries\nEmail: docs.export@example.org\n",
            "sheet-id": "Name,Passport\nLukas Weber,EN1234567\n",
            "slides-id": "Telefon: +491711234567\n",
        }
        return bodies[file_id].encode("utf-8")

    def download(self, file_id: str) -> bytes:
        raise AssertionError(f"Workspace file {file_id} should be exported, not downloaded.")

    @staticmethod
    def assert_folder_id(file_id: str) -> None:
        if file_id != "workspace-folder":
            raise AssertionError(file_id)


def _wait_for_scan(app: object, scan_id: str, trace_id: str) -> dict[str, object]:
    deadline = time.time() + 5
    result = app.handle("GET", f"/api/scans/{scan_id}", trace_id)
    while result["body"]["data"]["status"] == "running" and time.time() < deadline:
        time.sleep(0.05)
        result = app.handle("GET", f"/api/scans/{scan_id}", trace_id)
    return result


if __name__ == "__main__":
    unittest.main()
