from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from zipfile import ZipFile

from backend.lawdit.source_http import build_sqlite_app
from backend.lawdit.source_format_recognition import ExtractedDocumentContent
from backend.lawdit.source_image_ocr import ImageOcrResult
from backend.lawdit.source_legacy_office import LegacyOfficeExtractionResult
from backend.lawdit.source_video_ocr import VideoFrameOcrResult


class FormatRecognitionTests(unittest.TestCase):
    def test_office_open_xml_files_scan_without_ai_or_raw_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            _write_docx(root / "contact.docx", "Contact privacy.reviewer@example.org before export.")
            _write_xlsx(root / "finance.xlsx", "Finance IBAN DE89370400440532013000 must be reviewed.")
            _write_pptx(root / "support.pptx", "Support phone +491711234567 needs owner review.")
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
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
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_ooxml_scan_done")
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

    def test_legacy_office_files_scan_through_bounded_converter(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "legacy.doc").write_bytes(b"fake-doc")
            (root / "legacy.xls").write_bytes(b"fake-xls")
            (root / "legacy.ppt").write_bytes(b"fake-ppt")
            db_path = Path(directory) / "lawdit.sqlite3"

            def fake_legacy_extract(_body: bytes, name: str, file_format: str) -> LegacyOfficeExtractionResult:
                text_by_format = {
                    "doc": "Legacy doc email privacy.legacy-doc@example.org",
                    "xls": "Legacy xls IBAN DE89370400440532013000",
                    "ppt": "Legacy ppt phone +491711234567",
                }
                text = text_by_format[file_format]
                return LegacyOfficeExtractionResult(
                    text,
                    locations=({"format": file_format, "label": f"Legacy {file_format.upper()} text", "start": 0, "end": len(text)},),
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}), mock.patch(
                "backend.lawdit.source_format_recognition.extract_legacy_office_text",
                side_effect=fake_legacy_extract,
            ):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_legacy_office_create",
                    json.dumps({
                        "sourceId": "source_legacy_office",
                        "name": "Legacy Office source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_legacy_office/connect-test", "trace_legacy_office_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_legacy_office_scan",
                    json.dumps({"sourceId": "source_legacy_office"}),
                    "application/json",
                )
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_legacy_office_done")
                findings = app.handle("GET", "/api/findings", "trace_legacy_office_findings")
                details = [
                    app.handle("GET", f"/api/findings/{finding['findingId']}", f"trace_legacy_office_detail_{index}")
                    for index, finding in enumerate(findings["body"]["data"])
                ]
                serialized = json.dumps({"scan": scan["body"], "details": [detail["body"] for detail in details]})

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}

        self.assertEqual(len(findings["body"]["data"]), 3)
        self.assertEqual(extraction["successfulFiles"], 3)
        self.assertEqual(extraction["unsupportedFiles"], 0)
        self.assertEqual(extraction["recognitionDifficulty"]["hard"], 3)
        self.assertEqual(extraction["modelCalls"], 0)
        self.assertIn("doc", formats)
        self.assertIn("xls", formats)
        self.assertIn("ppt", formats)
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("privacy.legacy-doc@example.org", serialized)
        self.assertNotIn("DE89370400440532013000", serialized)
        self.assertNotIn("+491711234567", serialized)

    def test_structured_text_like_files_scan_multilingual_labels_with_anchors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contacts.csv").write_text("field,value\n姓名：王芳\n电话：13800138000\n", encoding="utf-8")
            (root / "case.json").write_text(
                '{"Correo electrónico":"privacidad.structured@example.org","Gehalt":"EUR 3200.00"}',
                encoding="utf-8",
            )
            (root / "profile.html").write_text(
                "<section><p>Téléphone: +33123456789</p><p>Adresse: 18 Rue Example</p></section>",
                encoding="utf-8",
            )
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_structured_text_create",
                    json.dumps({
                        "sourceId": "source_structured_text",
                        "name": "Structured text source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_structured_text/connect-test", "trace_structured_text_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_structured_text_scan",
                    json.dumps({"sourceId": "source_structured_text"}),
                    "application/json",
                )
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_structured_text_done")
                findings = app.handle("GET", "/api/findings", "trace_structured_text_findings")
                details = [
                    app.handle("GET", f"/api/findings/{finding['findingId']}", f"trace_structured_text_detail_{index}")
                    for index, finding in enumerate(findings["body"]["data"])
                ]
                serialized = json.dumps({"scan": scan["body"], "details": [detail["body"] for detail in details]}, ensure_ascii=False)

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}
        all_signals = [
            signal
            for detail in details
            for signal in detail["body"]["data"]["signals"]
        ]

        self.assertEqual(len(findings["body"]["data"]), 3)
        self.assertEqual(extraction["successfulFiles"], 3)
        self.assertEqual(extraction["recognitionDifficulty"]["easy"], 3)
        self.assertIn("csv", formats)
        self.assertIn("json", formats)
        self.assertIn("html", formats)
        anchor_types = {
            signal.get("evidenceAnchor", {}).get("selector", {}).get("type")
            for signal in all_signals
        }
        self.assertIn("tableCell", anchor_types)
        self.assertIn("structurePath", anchor_types)
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("privacidad.structured@example.org", serialized)
        self.assertNotIn("+33123456789", serialized)

    def test_image_ocr_scan_counts_hard_difficulty_without_raw_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "badge.png").write_bytes(b"not-a-real-image")
            db_path = Path(directory) / "lawdit.sqlite3"

            image_text = "Scanned visitor badge privacy.image@example.org"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}), mock.patch(
                "backend.lawdit.source_format_recognition.extract_image_content",
                return_value=ImageOcrResult(
                    image_text,
                    text_locations=({"format": "image_ocr", "label": "Image OCR text", "start": 0, "end": len(image_text)},),
                ),
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
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_image_scan_done")
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

    def test_bounded_large_pdf_is_not_rejected_by_text_stream_limit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "visual-report.pdf").write_bytes(b"%PDF-1.7\n" + (b"0" * 1_200_000))
            db_path = Path(directory) / "lawdit.sqlite3"
            extracted_text = "Passport: EN1234567"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}), mock.patch(
                "backend.lawdit.source_documents.extract_document_content",
                return_value=ExtractedDocumentContent(
                    extracted_text,
                    "pdf_text_layer",
                    "pdf_text_layer",
                    "moderate",
                    text_locations=({"format": "pdf_text_layer", "label": "Page 1", "start": 0, "end": len(extracted_text), "page": 1},),
                ),
            ):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_large_pdf_create",
                    json.dumps({
                        "sourceId": "source_large_pdf",
                        "name": "Large PDF source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_large_pdf/connect-test", "trace_large_pdf_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_large_pdf_scan",
                    json.dumps({"sourceId": "source_large_pdf"}),
                    "application/json",
                )
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_large_pdf_done")
                findings = app.handle("GET", "/api/findings", "trace_large_pdf_findings")

        extraction = scan["body"]["data"]["contentExtraction"]
        serialized = json.dumps({"scan": scan["body"], "findings": findings["body"]})

        self.assertEqual(extraction["successfulFiles"], 1)
        self.assertEqual(extraction["unsupportedFiles"], 0)
        self.assertEqual(len(findings["body"]["data"]), 1)
        self.assertNotIn("1 MB text extraction limit", serialized)
        self.assertNotIn("EN1234567", serialized)

    def test_video_transcript_scans_and_video_media_is_deferred(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "meeting.vtt").write_text(
                "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nVendor contact privacy.video@example.org\n",
                encoding="utf-8",
            )
            (root / "meeting.mp4").write_bytes(b"0" * 1_000_001)
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
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
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_video_scan_done")
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

    def test_video_media_scans_with_bounded_frame_ocr_when_available(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "walkthrough.mp4").write_bytes(b"fake-video")
            db_path = Path(directory) / "lawdit.sqlite3"
            video_text = "Walkthrough screen email privacy.video-frame@example.org"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}), mock.patch(
                "backend.lawdit.source_format_recognition.extract_video_frame_content",
                return_value=VideoFrameOcrResult(
                    video_text,
                    text_locations=({
                        "format": "video_ocr",
                        "label": "Frame 1 OCR text",
                        "start": 0,
                        "end": len(video_text),
                        "frameIndex": 1,
                        "page": 1,
                        "regions": ({
                            "start": 26,
                            "end": len(video_text),
                            "x": 64,
                            "y": 40,
                            "width": 420,
                            "height": 32,
                            "unit": "px",
                            "origin": "top_left",
                            "confidence": "ocr",
                            "pageWidth": 640,
                            "pageHeight": 240,
                        },),
                    },),
                ),
            ):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_video_frame_create",
                    json.dumps({
                        "sourceId": "source_video_frame",
                        "name": "Video frame source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_video_frame/connect-test", "trace_video_frame_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_video_frame_scan",
                    json.dumps({"sourceId": "source_video_frame"}),
                    "application/json",
                )
                scan = _wait_for_scan(app, started["body"]["data"]["scanId"], "trace_video_frame_done")
                findings = app.handle("GET", "/api/findings", "trace_video_frame_findings")
                detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_video_frame_detail")
                serialized = json.dumps({"scan": scan["body"], "detail": detail["body"]})

        extraction = scan["body"]["data"]["contentExtraction"]
        formats = {item["format"]: item for item in extraction["formatCounts"]}
        preview = detail["body"]["data"]["sourceReviewPreview"]

        self.assertEqual(len(findings["body"]["data"]), 1)
        self.assertEqual(extraction["successfulFiles"], 1)
        self.assertEqual(extraction["unsupportedFiles"], 0)
        self.assertEqual(extraction["ocrDeferredFiles"], 0)
        self.assertEqual(extraction["recognitionDifficulty"]["hard"], 1)
        self.assertIn("video_ocr", formats)
        self.assertEqual(preview["fileFormat"], "video_ocr")
        self.assertFalse(preview["rawContentExposed"])
        self.assertFalse(preview["pageImagesExposed"])
        self.assertIn("[REDACTED_", serialized)
        self.assertNotIn("privacy.video-frame@example.org", serialized)


def _wait_for_scan(app: object, scan_id: str, trace_id: str) -> dict:
    scan = {}
    for attempt in range(40):
        scan = app.handle("GET", f"/api/scans/{scan_id}", f"{trace_id}_{attempt}")
        if scan["body"]["data"].get("status") != "running":
            return scan
        time.sleep(0.25)
    return scan


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
