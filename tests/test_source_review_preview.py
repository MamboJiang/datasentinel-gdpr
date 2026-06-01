from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.source_documents import SourceDocument, SourceDocumentBatch
from backend.lawdit.source_http import build_sqlite_app
from backend.lawdit.source_review_preview import build_source_review_preview


class SourceReviewPreviewTests(unittest.TestCase):
    def test_source_preview_context_window_redacts_target_and_neighbor_values(self) -> None:
        text = "Requester: Alice Example; Contact Email: preview.ocr@example.org\n"
        email = "preview.ocr@example.org"
        email_start = text.index(email)
        signal = {
            "type": "email",
            "detector": "email_label",
            "confidence": 0.91,
            "snippet": "Email: [REDACTED_EMAIL]",
            "evidenceAnchor": {
                "anchorId": "anchor_preview_email",
                "format": "pdf_ocr",
                "label": "Email",
                "redactedText": "Email: [REDACTED_EMAIL]",
                "selector": {
                    "type": "textPosition",
                    "start": email_start,
                    "end": email_start + len(email),
                    "page": 1,
                    "sourceStart": email_start,
                    "sourceEnd": email_start + len(email),
                    "lineNumber": 1,
                    "columnNumber": email_start + 1,
                },
                "fallback": {
                    "label": "Page 1",
                    "redactedText": "Email: [REDACTED_EMAIL]",
                },
            },
        }

        preview = build_source_review_preview(
            SourceDocument(
                "image-only-review.pdf",
                "/private/source/image-only-review.pdf",
                text,
                128,
                "Local",
                file_format="pdf_ocr",
                extraction_method="pdf_page_image_ocr",
                recognition_difficulty="hard",
            ),
            [signal],
        )
        window = preview["anchors"][0]["contextWindow"]
        serialized = json.dumps(preview, ensure_ascii=False)

        self.assertEqual(window["redactedContext"], "Requester: [REDACTED_CONTEXT]; Contact Email: [REDACTED_EMAIL]")
        self.assertEqual(preview["anchors"][0]["selector"]["lineNumber"], 1)
        self.assertEqual(preview["anchors"][0]["selector"]["columnNumber"], email_start + 1)
        self.assertEqual(window["rawContentExposed"], False)
        self.assertGreaterEqual(window["highlightStart"], 0)
        self.assertGreater(window["highlightEnd"], window["highlightStart"])
        self.assertEqual(preview["contextWindows"][0], window)
        self.assertNotIn(email, serialized)
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("/private/source", serialized)

    def test_prelaunch_finding_detail_includes_redacted_source_preview_package(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "placeholder.txt").write_text("placeholder", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"
            source_path = root / "image-only-review.pdf"
            text = "Contact Email: preview.ocr@example.org\n"
            email_start = text.index("preview.ocr@example.org")

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                return SourceDocumentBatch(
                    documents=[SourceDocument(
                        "image-only-review.pdf",
                        str(source_path),
                        text,
                        128,
                        "Local",
                        file_format="pdf_ocr",
                        extraction_method="pdf_page_image_ocr",
                        recognition_difficulty="hard",
                        text_locations=({
                            "format": "pdf_ocr",
                            "label": "Page 1",
                            "start": 0,
                            "end": len(text),
                            "page": 1,
                            "regions": ({
                                "start": email_start,
                                "end": len(text.strip()),
                                "x": 144,
                                "y": 88,
                                "width": 224,
                                "height": 24,
                                "pageWidth": 1654,
                                "pageHeight": 2339,
                                "unit": "px",
                                "origin": "top_left",
                                "confidence": "ocr",
                                "ocrConfidence": 90.1,
                            },),
                        },),
                    )],
                    total_files=1,
                    total_bytes=128,
                    unsupported_files=0,
                    warnings=[],
                    family="Local",
                    extraction_method="fixture_pdf_ocr",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_review_preview_source_create",
                    json.dumps({
                        "sourceId": "source_review_preview",
                        "name": "Review preview source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_review_preview/connect-test", "trace_review_preview_connect")
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_review_preview_scan",
                        json.dumps({"sourceId": "source_review_preview"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    findings = app.handle("GET", "/api/findings", "trace_review_preview_findings")
                    detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_review_preview_detail")

        preview = detail["body"]["data"]["sourceReviewPreview"]
        serialized = json.dumps(detail["body"], ensure_ascii=False)

        self.assertEqual(started["status"], 202)
        self.assertEqual(preview["fileFormat"], "pdf_ocr")
        self.assertEqual(preview["redactionMode"], "anchor_only")
        self.assertFalse(preview["rawContentExposed"])
        self.assertFalse(preview["pageImagesExposed"])
        self.assertEqual(preview["pages"][0]["coordinateSystem"], "image_pixels_top_left")
        self.assertEqual(preview["pages"][0]["regions"][0]["region"]["ocrConfidence"], 90.1)
        self.assertEqual(preview["textRanges"][0]["selector"]["sourceStart"], email_start)
        self.assertEqual(preview["anchors"][0]["contextWindow"]["redactedContext"], "Contact Email: [REDACTED_EMAIL]")
        self.assertEqual(preview["contextWindows"][0]["anchorId"], preview["anchors"][0]["anchorId"])
        self.assertNotIn("preview.ocr@example.org", serialized)
        self.assertNotIn(str(root), serialized)
        self.assertNotIn(str(source_path), serialized)


if __name__ == "__main__":
    unittest.main()
