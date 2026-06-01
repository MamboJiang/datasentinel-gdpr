from __future__ import annotations

import json
import unittest
from unittest import mock

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_format_recognition import extract_document_content
from backend.datasentinel.source_pdf_text import PdfExtractionIssue


class PdfRegionAnchorTests(unittest.TestCase):
    def test_mixed_pdf_ocr_failure_returns_text_layer_with_deferred_warning(self) -> None:
        text_page = "Contact Email: text.layer@example.org\n"

        class ImageTextPage:
            def get(self, key: str):
                if key == "/Resources":
                    return {"/XObject": {"/Im1": {"/Subtype": "/Image"}}}
                return None

            def extract_text(self, visitor_text=None):
                if visitor_text:
                    visitor_text(text_page, [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 72, 720], None, 12)
                return text_page

        class MixedPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [ImageTextPage()]

        with mock.patch(
            "backend.datasentinel.source_pdf_text._ocr_selected_page_records",
            side_effect=PdfExtractionIssue("pdftoppm is not installed on this host.", ocr_deferred=True),
        ):
            extracted = extract_document_content(
                body=b"%PDF-1.7 image-text",
                content_type="application/pdf",
                name="image-text.pdf",
                pdf_reader=MixedPdfReader,
            )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        serialized = json.dumps(signals)

        self.assertEqual(extracted.file_format, "pdf_text_layer")
        self.assertEqual(extracted.extraction_method, "pdf_text_layer")
        self.assertEqual(extracted.recognition_difficulty, "hard")
        self.assertTrue(extracted.ocr_deferred)
        self.assertIn("mixed PDF page OCR deferred", extracted.warnings[0])
        self.assertEqual(signals[0]["evidenceAnchor"]["format"], "pdf_text_layer")
        self.assertNotIn("text.layer@example.org", serialized)

    def test_mixed_pdf_image_text_page_merges_overlay_ocr_regions(self) -> None:
        text_page = "Travel cover page\n"
        ocr_text = "姓名：王芳\n地址：北京市朝阳区建国路88号\nPassport: EN1234567"
        passport_start = ocr_text.index("EN1234567")

        class ImageTextPage:
            def get(self, key: str):
                if key == "/Resources":
                    return {"/XObject": {"/Im1": {"/Subtype": "/Image"}}}
                return None

            def extract_text(self, visitor_text=None):
                if visitor_text:
                    visitor_text(text_page, [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 72, 720], None, 12)
                return text_page

        class MixedPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [ImageTextPage()]

        ocr_records = {
            1: {
                "text": ocr_text,
                "format": "pdf_ocr",
                "regions": ({
                    "start": passport_start,
                    "end": len(ocr_text),
                    "x": 160,
                    "y": 120,
                    "width": 260,
                    "height": 30,
                    "pageWidth": 1654,
                    "pageHeight": 2339,
                    "unit": "px",
                    "origin": "top_left",
                    "confidence": "ocr",
                },),
            }
        }

        with mock.patch(
            "backend.datasentinel.source_pdf_text._ocr_selected_page_records",
            return_value=ocr_records,
        ) as ocr:
            extracted = extract_document_content(
                body=b"%PDF-1.7 image-text",
                content_type="application/pdf",
                name="image-text.pdf",
                pdf_reader=MixedPdfReader,
            )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        passport_signal = next(signal for signal in signals if signal["type"] == "passport_number")
        selector = passport_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "pdf_mixed")
        self.assertEqual(extracted.extraction_method, "pdf_text_layer_with_page_ocr")
        self.assertTrue({"person_name", "address", "passport_number"}.issubset(signal_types))
        self.assertEqual(passport_signal["evidenceAnchor"]["format"], "pdf_ocr")
        self.assertEqual(selector["page"], 1)
        self.assertEqual(selector["sourceStart"], len(text_page) + 1 + passport_start)
        self.assertEqual(selector["pageRegion"]["origin"], "top_left")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)
        self.assertNotIn("EN1234567", serialized)
        ocr.assert_called_once_with(b"%PDF-1.7 image-text", "image-text.pdf", [1])

    def test_mixed_pdf_blank_page_uses_page_ocr_regions_without_raw_values(self) -> None:
        text_page = "Cover page without personal data\n"
        ocr_text = "Contact privacy.mixed@example.org"
        email_start = ocr_text.index("privacy.mixed@example.org")

        class TextPage:
            def extract_text(self, visitor_text=None):
                if visitor_text:
                    visitor_text(text_page, [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 72, 720], None, 12)
                return text_page

        class BlankPage:
            def extract_text(self, visitor_text=None):
                return ""

        class MixedPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [TextPage(), BlankPage()]

        ocr_records = {
            2: {
                "text": ocr_text,
                "format": "pdf_ocr",
                "regions": ({
                    "start": email_start,
                    "end": len(ocr_text),
                    "x": 120,
                    "y": 80,
                    "width": 240,
                    "height": 24,
                    "pageWidth": 1654,
                    "pageHeight": 2339,
                    "unit": "px",
                    "origin": "top_left",
                    "confidence": "ocr",
                    "ocrConfidence": 91.7,
                },),
            }
        }

        with mock.patch(
            "backend.datasentinel.source_pdf_text._ocr_selected_page_records",
            return_value=ocr_records,
        ) as ocr:
            extracted = extract_document_content(
                body=b"%PDF-1.7 mixed",
                content_type="application/pdf",
                name="mixed.pdf",
                pdf_reader=MixedPdfReader,
            )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        email_signal = next(signal for signal in signals if signal["type"] == "email")
        selector = email_signal["evidenceAnchor"]["selector"]
        region = selector["pageRegion"]
        serialized = json.dumps(signals)

        self.assertEqual(extracted.file_format, "pdf_mixed")
        self.assertEqual(extracted.extraction_method, "pdf_text_layer_with_page_ocr")
        self.assertEqual(extracted.recognition_difficulty, "hard")
        self.assertEqual(email_signal["evidenceAnchor"]["format"], "pdf_ocr")
        self.assertEqual(email_signal["evidenceAnchor"]["fallback"]["label"], "Page 2")
        self.assertEqual(selector["page"], 2)
        self.assertEqual(selector["sourceStart"], email_start)
        self.assertEqual(region["origin"], "top_left")
        self.assertEqual(region["unit"], "px")
        self.assertEqual(region["pageWidth"], 1654)
        self.assertEqual(region["ocrConfidence"], 91.7)
        self.assertNotIn("privacy.mixed@example.org", serialized)
        ocr.assert_called_once_with(b"%PDF-1.7 mixed", "mixed.pdf", [2])

    def test_pdf_text_layer_region_selector_uses_scan_time_coordinates_without_raw_values(self) -> None:
        page_text = "Contact Email: pdf.region@example.org\n"

        class Page:
            def extract_text(self, visitor_text=None):
                if visitor_text:
                    visitor_text(page_text, [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 72, 720], None, 12)
                return page_text

        class TextPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [Page()]

        extracted = extract_document_content(
            body=b"%PDF-1.7 text-layer",
            content_type="application/pdf",
            name="region-anchor.pdf",
            pdf_reader=TextPdfReader,
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        email_signal = next(signal for signal in signals if signal["detector"] == "email_label")
        selector = email_signal["evidenceAnchor"]["selector"]
        region = selector["pageRegion"]
        serialized = json.dumps(signals)

        self.assertEqual(selector["page"], 1)
        self.assertEqual(selector["sourceStart"], page_text.index("pdf.region@example.org"))
        self.assertEqual(region["unit"], "pt")
        self.assertEqual(region["origin"], "bottom_left")
        self.assertEqual(region["confidence"], "estimated")
        self.assertGreaterEqual(region["x"], 0)
        self.assertGreater(region["width"], 0)
        self.assertGreater(region["height"], 0)
        self.assertNotIn("pdf.region@example.org", serialized)


if __name__ == "__main__":
    unittest.main()
