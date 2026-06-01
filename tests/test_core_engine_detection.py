from __future__ import annotations

import json
import subprocess
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.deterministic_signals import detect_signals, sanitize_public_signal
from backend.lawdit.ocr_capabilities import ocr_capabilities
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_documents import SourceDocument, SourceDocumentBatch
from backend.lawdit.source_format_recognition import DocumentExtractionIssue, build_document_batch, extract_document_content
from backend.lawdit.source_http import build_sqlite_app
from backend.lawdit.source_image_ocr import extract_image_text
from backend.lawdit.source_pdf_text import PdfExtractionIssue, PdfExtractionResult


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"


class CoreEngineDetectionTests(unittest.TestCase):
    def test_multilingual_fixture_labels_detect_redacted_signals(self) -> None:
        cases = _multilingual_cases()

        for case in cases:
            with self.subTest(case=case["caseId"]):
                signals = detect_signals(str(case["text"]))
                signal_types = {signal["type"] for signal in signals}
                serialized = json.dumps(signals, ensure_ascii=False)

                self.assertTrue(set(case["expectedTypes"]).issubset(signal_types))
                self.assertIn("[REDACTED_", serialized)
                for raw_value in case["forbiddenValues"]:
                    self.assertNotIn(raw_value, serialized)

    def test_detected_signals_include_public_safe_text_position_anchors(self) -> None:
        text = "姓名：王芳\nContact Email: privacy.anchor@example.org\nNotes: keep this for review\n"

        signals = detect_signals(text)
        serialized = json.dumps(signals, ensure_ascii=False)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        name_selector = name_signal["evidenceAnchor"]["selector"]

        self.assertTrue(all("evidenceAnchor" in signal for signal in signals))
        self.assertEqual(name_selector["type"], "textPosition")
        self.assertEqual(name_selector["start"], text.index("王芳"))
        self.assertEqual(name_selector["end"], text.index("王芳") + len("王芳"))
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "Line 1")
        self.assertIn("[REDACTED_", serialized)
        self.assertIn("textPosition", serialized)
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("privacy.anchor@example.org", serialized)

    def test_inline_multilingual_labels_detect_multiple_static_text_fields(self) -> None:
        text = "姓名：王芳 电话：13800138000 地址：北京市朝阳区建国路88号\n"

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)
        address_signal = next(signal for signal in signals if signal["type"] == "address")
        address_selector = address_signal["evidenceAnchor"]["selector"]

        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertEqual(address_selector["type"], "textPosition")
        self.assertEqual(address_selector["start"], text.index("北京市朝阳区建国路88号"))
        self.assertEqual(address_selector["end"], text.index("北京市朝阳区建国路88号") + len("北京市朝阳区建国路88号"))
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)

    def test_ocr_spaced_multilingual_labels_detect_when_punctuation_is_missing(self) -> None:
        text = "姓名 王芳 电话 13800138000 地址 北京市朝阳区建国路88号\n"

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertIn("multilingual_person_label", serialized)
        self.assertIn("multilingual_address_label", serialized)
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)

    def test_ocr_separatorless_multilingual_labels_detect_when_character_spacing_is_removed(self) -> None:
        text = "姓名王芳电话13800138000地址北京市朝阳区建国路88号\n"

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")

        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["start"], text.index("王芳"))
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)

    def test_dash_delimited_static_text_labels_detect_without_raw_values(self) -> None:
        text = "Name - Alice Example\nPhone - +1 415 555 0134\nAddress - 1 Market St\n"

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("+1 415 555 0134", serialized)
        self.assertNotIn("1 Market St", serialized)

    def test_contextual_labels_suppress_weaker_overlapping_regex_types(self) -> None:
        text = (
            "Bankkonto: DE89370400440532013000\n"
            "Salaris: EUR 62000\n"
            "BSN: 123456782\n"
            "Project budget: USD 120000\n"
            "Product SKU: AB12345678\n"
        )

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}

        self.assertIn("bank_account", signal_types)
        self.assertIn("salary_compensation", signal_types)
        self.assertIn("national_identifier", signal_types)
        self.assertNotIn("iban_like", signal_types)
        self.assertNotIn("expense_amount", signal_types)
        self.assertNotIn("tax_id", signal_types)

    def test_signal_sanitizer_redacts_persisted_anchor_text(self) -> None:
        signal = {
            "type": "email",
            "detector": "email_label",
            "confidence": 0.86,
            "snippet": "Contact: [REDACTED_EMAIL]",
            "evidenceAnchor": {
                "anchorId": "anchor_old",
                "format": "text",
                "label": "Email",
                "redactedText": "Contact: privacy.anchor@example.org",
                "selector": {"type": "textPosition", "start": 9, "end": 35},
                "fallback": {"label": "Line 2", "redactedText": "privacy.anchor@example.org"},
            },
        }

        sanitized = sanitize_public_signal(signal)
        serialized = json.dumps(sanitized, ensure_ascii=False)

        self.assertEqual(sanitized["evidenceAnchor"]["selector"]["type"], "textPosition")
        self.assertEqual(sanitized["evidenceAnchor"]["fallback"]["label"], "Line 2")
        self.assertIn("[REDACTED_EMAIL]", serialized)
        self.assertNotIn("privacy.anchor@example.org", serialized)

    def test_pdf_text_layer_locations_enrich_signal_anchors_with_page_context(self) -> None:
        page2_text = "Contact Email: pdf.anchor@example.org\n"

        class Page:
            def __init__(self, text: str) -> None:
                self.text = text

            def extract_text(self) -> str:
                return self.text

        class TextPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [
                    Page("Cover page\n"),
                    Page(page2_text),
                ]

        extracted = extract_document_content(
            body=b"%PDF-1.7 text-layer",
            content_type="application/pdf",
            name="page-anchor.pdf",
            pdf_reader=TextPdfReader,
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        email_signal = next(signal for signal in signals if signal["detector"] == "email_label")
        selector = email_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals)

        self.assertEqual(extracted.file_format, "pdf_text_layer")
        self.assertEqual(email_signal["evidenceAnchor"]["format"], "pdf_text_layer")
        self.assertEqual(email_signal["evidenceAnchor"]["fallback"]["label"], "Page 2")
        self.assertEqual(selector["type"], "textPosition")
        self.assertEqual(selector["page"], 2)
        self.assertEqual(selector["sourceStart"], page2_text.index("pdf.anchor@example.org"))
        self.assertEqual(selector["sourceEnd"], selector["sourceStart"] + len("pdf.anchor@example.org"))
        self.assertNotIn("pdf.anchor@example.org", serialized)

    def test_prelaunch_scan_assembles_multilingual_findings_without_raw_values(self) -> None:
        cases = _multilingual_cases()

        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "placeholder.txt").write_text("placeholder", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                documents = [
                    SourceDocument(
                        f"{case['caseId']}.txt",
                        f"drive_manifest:{case['caseId']}",
                        str(case["text"]),
                        len(str(case["text"]).encode("utf-8")),
                        "GDPR_Data_Samples_Main",
                    )
                    for case in cases
                ]
                return SourceDocumentBatch(
                    documents=documents,
                    total_files=len(documents),
                    total_bytes=sum(document.size_bytes for document in documents),
                    unsupported_files=0,
                    warnings=[],
                    family="GDPR_Data_Samples_Main",
                    extraction_method="fixture_multilingual_text",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_multilingual_source_create",
                    json.dumps({
                        "sourceId": "source_multilingual_cases",
                        "name": "GDPR Data Samples Main multilingual cases",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_multilingual_cases/connect-test", "trace_multilingual_connect")
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_multilingual_scan",
                        json.dumps({"sourceId": "source_multilingual_cases"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_multilingual_done")
                    findings = app.handle("GET", "/api/findings", "trace_multilingual_findings")
                    first_detail = app.handle(
                        "GET",
                        f"/api/findings/{findings['body']['data'][0]['findingId']}",
                        "trace_multilingual_detail",
                    )

        serialized = json.dumps({"scan": scan["body"], "findings": findings["body"], "detail": first_detail["body"]}, ensure_ascii=False)
        all_expected = {signal_type for case in cases for signal_type in case["expectedTypes"]}
        signal_types = {item["type"] for item in scan["body"]["data"]["signalDetection"]["signalTypeCounts"]}

        self.assertEqual(started["status"], 202)
        self.assertEqual(findings["body"]["pagination"]["total"], len(cases))
        self.assertTrue(all_expected.issubset(signal_types))
        self.assertIn("[REDACTED_", serialized)
        self.assertTrue(any(
            signal.get("evidenceAnchor", {}).get("selector", {}).get("type") == "textPosition"
            for signal in first_detail["body"]["data"]["signals"]
        ))
        for case in cases:
            for raw_value in case["forbiddenValues"]:
                self.assertNotIn(raw_value, serialized)

    def test_prelaunch_scan_exposes_pdf_page_anchor_context_without_raw_values(self) -> None:
        text = "Cover\nContact Email: pdf.detail@example.org\n"
        page_start = text.index("Contact Email")

        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "placeholder.pdf").write_bytes(b"%PDF-1.7")
            db_path = Path(directory) / "lawdit.sqlite3"

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                document = SourceDocument(
                    name="page_anchor.pdf",
                    source_path="drive_manifest:page_anchor",
                    text=text,
                    size_bytes=len(text.encode("utf-8")),
                    family="PDF_Text_Layer",
                    file_format="pdf_text_layer",
                    extraction_method="pdf_text_layer",
                    recognition_difficulty="moderate",
                    text_locations=({"format": "pdf_text_layer", "label": "Page 2", "start": page_start, "end": len(text), "page": 2},),
                )
                return SourceDocumentBatch(
                    documents=[document],
                    total_files=1,
                    total_bytes=document.size_bytes,
                    unsupported_files=0,
                    warnings=[],
                    family="PDF_Text_Layer",
                    extraction_method="fixture_pdf_text_layer",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_pdf_anchor_source_create",
                    json.dumps({
                        "sourceId": "source_pdf_anchor",
                        "name": "PDF page anchor source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_pdf_anchor/connect-test", "trace_pdf_anchor_connect")
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_pdf_anchor_scan",
                        json.dumps({"sourceId": "source_pdf_anchor"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    findings = app.handle("GET", "/api/findings", "trace_pdf_anchor_findings")
                    detail = app.handle(
                        "GET",
                        f"/api/findings/{findings['body']['data'][0]['findingId']}",
                        "trace_pdf_anchor_detail",
                    )

        signal = next(item for item in detail["body"]["data"]["signals"] if item["detector"] == "email_label")
        selector = signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(detail["body"])

        self.assertEqual(started["status"], 202)
        self.assertEqual(signal["evidenceAnchor"]["format"], "pdf_text_layer")
        self.assertEqual(signal["evidenceAnchor"]["fallback"]["label"], "Page 2")
        self.assertEqual(selector["page"], 2)
        self.assertNotIn("pdf.detail@example.org", serialized)

    def test_pdf_without_text_layer_can_fall_back_to_local_ocr(self) -> None:
        ocr_text = "姓名：王芳\n电话：13800138000"

        class EmptyPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [mock.Mock(extract_text=lambda: "")]

        with mock.patch(
            "backend.lawdit.source_pdf_text._ocr_result",
            return_value=PdfExtractionResult(
                ocr_text,
                "pdf_ocr",
                "pdf_page_image_ocr",
                "hard",
                text_locations=({"format": "pdf_ocr", "label": "Page 1", "start": 0, "end": len(ocr_text), "page": 1},),
            ),
        ):
            extracted = extract_document_content(
                body=b"%PDF-1.7 image-only",
                content_type="application/pdf",
                name="scan.pdf",
                pdf_reader=EmptyPdfReader,
            )

        signals = detect_signals(extracted.text)
        signal_types = {signal["type"] for signal in signals}

        self.assertEqual(extracted.file_format, "pdf_ocr")
        self.assertEqual(extracted.extraction_method, "pdf_page_image_ocr")
        self.assertEqual(extracted.recognition_difficulty, "hard")
        self.assertIn("person_name", signal_types)
        self.assertIn("phone_number", signal_types)

    def test_pdf_ocr_missing_tools_remains_recoverable_deferred_work(self) -> None:
        class EmptyPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [mock.Mock(extract_text=lambda: "")]

        with mock.patch(
            "backend.lawdit.source_pdf_text._ocr_result",
            side_effect=PdfExtractionIssue("scan.pdf requires PDF OCR, but pdftoppm is not installed on this host.", ocr_deferred=True),
        ):
            with self.assertRaises(DocumentExtractionIssue) as raised:
                extract_document_content(
                    body=b"%PDF-1.7 image-only",
                    content_type="application/pdf",
                    name="scan.pdf",
                    pdf_reader=EmptyPdfReader,
                )

        self.assertEqual(raised.exception.recognition_difficulty, "hard")
        self.assertTrue(raised.exception.ocr_deferred)
        self.assertIn("pdftoppm is not installed", raised.exception.detail)

    def test_local_ocr_can_select_multilingual_tesseract_languages(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout=(
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "1\t1\t0\t0\t0\t0\t0\t0\t640\t480\t-1\t\n"
                "5\t1\t1\t1\t1\t1\t12\t20\t96\t24\t92.5\t姓名：王芳\n"
            ),
        )

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+chi_sim"},
        ), mock.patch(
            "backend.lawdit.ocr_capabilities.shutil.which",
            return_value="/usr/bin/tesseract",
        ), mock.patch(
            "backend.lawdit.source_image_ocr.subprocess.run",
            return_value=completed,
        ) as run:
            text = extract_image_text(b"image-bytes", "badge.png")

        command = run.call_args.args[0]
        self.assertEqual(text, "姓名：王芳")
        self.assertIn("-l", command)
        self.assertIn("eng+chi_sim", command)
        self.assertIn("tsv", command)

    def test_local_ocr_splits_large_language_bundle_and_continues_after_timeout(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout=(
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "1\t1\t0\t0\t0\t0\t0\t0\t640\t480\t-1\t\n"
                "5\t1\t1\t1\t1\t1\t12\t20\t96\t24\t92.5\t姓名：王芳\n"
            ),
        )
        calls: list[list[str]] = []

        def fake_tesseract(command: list[str], **kwargs: object) -> mock.Mock:
            calls.append(command)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            return completed

        large_language_bundle = "eng+chi_sim+deu+fra+spa+por+ita+nld+pol+jpn+kor+ara"
        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": large_language_bundle},
        ), mock.patch(
            "backend.lawdit.ocr_capabilities.shutil.which",
            return_value="/usr/bin/tesseract",
        ), mock.patch(
            "backend.lawdit.source_image_ocr.subprocess.run",
            side_effect=fake_tesseract,
        ):
            text = extract_image_text(b"image-bytes", "large-language-bundle.png")

        language_profiles = [command[command.index("-l") + 1] for command in calls if "-l" in command]

        self.assertEqual(text, "姓名：王芳")
        self.assertIn("eng+chi_sim+deu+fra+spa", language_profiles)
        self.assertGreaterEqual(len(language_profiles), 2)
        self.assertNotIn(large_language_bundle, language_profiles)

    def test_document_level_ocr_deferred_warning_is_counted_without_dropping_text_layer(self) -> None:
        document = SourceDocument(
            "mixed.pdf",
            "drive_manifest:mixed",
            "Contact Email: pdf.layer@example.org",
            4096,
            "Google_Drive",
            file_format="pdf_text_layer",
            extraction_method="pdf_text_layer",
            recognition_difficulty="hard",
            warnings=("mixed.pdf mixed PDF page OCR deferred: pdftoppm is not installed.",),
            ocr_deferred=True,
        )

        batch = build_document_batch(
            documents=[document],
            total_files=1,
            total_bytes=document.size_bytes,
            unsupported_files=0,
            warnings=[],
            family="Google_Drive",
            extraction_method="google_drive_export",
        )

        methods = {item["method"]: item for item in batch.method_counts or []}

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.warning_files, 1)
        self.assertEqual(batch.ocr_deferred_files, 1)
        self.assertEqual(batch.recognition_difficulty["hard"], 1)
        self.assertIn("mixed PDF page OCR deferred", batch.warnings[0])
        self.assertEqual(methods["pdf_text_layer"]["status"], "completed")
        self.assertEqual(methods["ocr_deferred"]["status"], "warning")

    def test_ocr_capability_report_reflects_mode_tools_and_languages(self) -> None:
        def fake_which(tool: str) -> str | None:
            return {"tesseract": "/usr/bin/tesseract", "pdftoppm": "/usr/bin/pdftoppm"}.get(tool)

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+chi_sim,deu"},
        ), mock.patch("backend.lawdit.ocr_capabilities.shutil.which", side_effect=fake_which):
            available = ocr_capabilities()

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "deferred", "LAWDIT_OCR_LANGS": "eng"},
        ), mock.patch("backend.lawdit.ocr_capabilities.shutil.which", side_effect=fake_which):
            deferred = ocr_capabilities()

        self.assertEqual(available["ocrMode"], "local")
        self.assertEqual(available["languagesConfigured"], ["eng", "chi_sim", "deu"])
        self.assertTrue(available["imageOcrAvailable"])
        self.assertTrue(available["pdfOcrAvailable"])
        self.assertEqual(deferred["ocrMode"], "deferred")
        self.assertFalse(deferred["imageOcrAvailable"])
        self.assertFalse(deferred["pdfOcrAvailable"])


def _multilingual_cases() -> list[dict[str, object]]:
    payload = json.loads((FIXTURE_DIR / "core_multilingual_cases.json").read_text(encoding="utf-8"))
    return list(payload["cases"])


if __name__ == "__main__":
    unittest.main()
