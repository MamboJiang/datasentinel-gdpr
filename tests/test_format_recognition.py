from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from zipfile import ZipFile

from backend.datasentinel.source_http import build_sqlite_app


class FormatRecognitionTests(unittest.TestCase):
    def test_office_open_xml_files_scan_without_ai_or_raw_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            _write_docx(root / "contact.docx", "Contact privacy.reviewer@example.org before export.")
            _write_xlsx(root / "finance.xlsx", "Finance IBAN DE89370400440532013000 must be reviewed.")
            _write_pptx(root / "support.pptx", "Support phone +491711234567 needs owner review.")
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_ooxml_create",
                    json.dumps({
                        "sourceId": "source_ooxml",
                        "name": "OOXML source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                connected = app.handle("POST", "/api/sources/source_ooxml/connect-test", "trace_ooxml_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_ooxml_scan",
                    json.dumps({"sourceId": "source_ooxml"}),
                    "application/json",
                )
                time.sleep(1.1)
                scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_ooxml_scan_done")
                findings = app.handle("GET", "/api/findings", "trace_ooxml_findings")
                first_detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_ooxml_detail")
                evaluation = app.handle("GET", "/api/evaluation/runs/latest", "trace_ooxml_eval")
                serialized = json.dumps({"scan": scan["body"], "detail": first_detail["body"]})

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}

        self.assertEqual(created["status"], 201)
        self.assertEqual(connected["body"]["data"]["connectionStatus"], "connected")
        self.assertEqual(started["status"], 202)
        self.assertEqual(len(findings["body"]["data"]), 3)
        self.assertEqual(extraction["successfulFiles"], 3)
        self.assertEqual(extraction["recognitionDifficulty"]["moderate"], 3)
        self.assertEqual(extraction["recognitionDifficulty"]["easy"], 0)
        self.assertEqual(extraction["aiAssistanceUsed"], False)
        self.assertEqual(extraction["modelCalls"], 0)
        self.assertEqual(evaluation["body"]["data"]["resourceIntensity"]["modelCalls"], 0)
        self.assertIn("docx", formats)
        self.assertIn("xlsx", formats)
        self.assertIn("pptx", formats)
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("privacy.reviewer@example.org", serialized)
        self.assertNotIn("DE89370400440532013000", serialized)
        self.assertNotIn("+491711234567", serialized)

    def test_image_ocr_scan_counts_hard_difficulty_without_raw_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "badge.png").write_bytes(b"not-a-real-image")
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}), mock.patch(
                "backend.datasentinel.source_format_recognition.extract_image_text",
                return_value="Scanned visitor badge privacy.image@example.org",
            ):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_image_create",
                    json.dumps({
                        "sourceId": "source_image",
                        "name": "Image source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_image/connect-test", "trace_image_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_image_scan",
                    json.dumps({"sourceId": "source_image"}),
                    "application/json",
                )
                time.sleep(1.1)
                scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_image_scan_done")
                findings = app.handle("GET", "/api/findings", "trace_image_findings")
                detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_image_detail")
                serialized = json.dumps({"scan": scan["body"], "detail": detail["body"]})

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}

        self.assertEqual(len(findings["body"]["data"]), 1)
        self.assertEqual(extraction["successfulFiles"], 1)
        self.assertEqual(extraction["ocrDeferredFiles"], 0)
        self.assertEqual(extraction["recognitionDifficulty"]["hard"], 1)
        self.assertEqual(extraction["aiAssistanceUsed"], False)
        self.assertEqual(extraction["modelCalls"], 0)
        self.assertIn("image_ocr", formats)
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("privacy.image@example.org", serialized)

    def test_video_transcript_scans_and_video_media_is_deferred(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "meeting.vtt").write_text(
                "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nVendor contact privacy.video@example.org\n",
                encoding="utf-8",
            )
            (root / "meeting.mp4").write_bytes(b"0" * 1_000_001)
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_video_create",
                    json.dumps({
                        "sourceId": "source_video",
                        "name": "Video source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_video/connect-test", "trace_video_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_video_scan",
                    json.dumps({"sourceId": "source_video"}),
                    "application/json",
                )
                time.sleep(1.1)
                scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_video_scan_done")
                findings = app.handle("GET", "/api/findings", "trace_video_findings")
                detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_video_detail")
                serialized = json.dumps({"scan": scan["body"], "detail": detail["body"]})

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}

        self.assertEqual(len(findings["body"]["data"]), 1)
        self.assertEqual(extraction["successfulFiles"], 1)
        self.assertEqual(extraction["unsupportedFiles"], 1)
        self.assertEqual(extraction["ocrDeferredFiles"], 1)
        self.assertEqual(extraction["recognitionDifficulty"]["moderate"], 1)
        self.assertEqual(extraction["recognitionDifficulty"]["hard"], 1)
        self.assertEqual(extraction["modelCalls"], 0)
        self.assertIn("video_transcript", formats)
        self.assertIn("ocr_deferred", formats)
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("privacy.video@example.org", serialized)


def _write_docx(path: Path, text: str) -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>"""
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def _write_xlsx(path: Path, text: str) -> None:
    shared = f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>{text}</t></si>
</sst>"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData>
</worksheet>"""
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def _write_pptx(path: Path, text: str) -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>"""
    with ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", xml)


if __name__ == "__main__":
    unittest.main()
