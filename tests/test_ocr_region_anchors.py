from __future__ import annotations

import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content
from backend.lawdit.source_image_ocr import ImageOcrResult

try:
    from PIL import Image
except Exception:  # pragma: no cover - depends on local test environment
    Image = None  # type: ignore[assignment]


class OcrRegionAnchorTests(unittest.TestCase):
    def test_image_ocr_regions_enrich_signal_anchors_without_raw_values(self) -> None:
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "1\t1\t0\t0\t0\t0\t0\t0\t800\t600\t-1\t\n"
            "5\t1\t1\t1\t1\t1\t40\t36\t64\t20\t91.2\tContact\n"
            "5\t1\t1\t1\t1\t2\t120\t36\t218\t20\t93.4\tprivacy.image@example.org\n"
        )
        completed = mock.Mock(returncode=0, stdout=tsv)

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+deu"},
        ), mock.patch(
            "backend.lawdit.ocr_capabilities.shutil.which",
            return_value="/usr/bin/tesseract",
        ), mock.patch(
            "backend.lawdit.source_image_ocr.subprocess.run",
            return_value=completed,
        ) as run:
            extracted = extract_document_content(body=b"image", content_type="image/png", name="badge.png")

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        email_signal = next(signal for signal in signals if signal["type"] == "email")
        selector = email_signal["evidenceAnchor"]["selector"]
        region = selector["pageRegion"]
        serialized = json.dumps(signals)

        self.assertEqual(extracted.file_format, "image_ocr")
        self.assertEqual(extracted.text, "Contact privacy.image@example.org")
        self.assertEqual(selector["sourceStart"], extracted.text.index("privacy.image@example.org"))
        self.assertEqual(region["x"], 120)
        self.assertEqual(region["y"], 36)
        self.assertEqual(region["width"], 218)
        self.assertEqual(region["height"], 20)
        self.assertEqual(region["unit"], "px")
        self.assertEqual(region["origin"], "top_left")
        self.assertEqual(region["confidence"], "ocr")
        self.assertEqual(region["ocrConfidence"], 93.4)
        self.assertNotIn("privacy.image@example.org", serialized)
        self.assertIn("tsv", run.call_args.args[0])

    def test_image_ocr_joins_cjk_character_words_for_separatorless_label_detection(self) -> None:
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "1\t1\t0\t0\t0\t0\t0\t0\t900\t300\t-1\t\n"
            "5\t1\t1\t1\t1\t1\t20\t30\t18\t20\t91\t姓\n"
            "5\t1\t1\t1\t1\t2\t40\t30\t18\t20\t91\t名\n"
            "5\t1\t1\t1\t1\t3\t62\t30\t18\t20\t91\t王\n"
            "5\t1\t1\t1\t1\t4\t84\t30\t18\t20\t91\t芳\n"
            "5\t1\t1\t1\t1\t5\t126\t30\t18\t20\t91\t电\n"
            "5\t1\t1\t1\t1\t6\t148\t30\t18\t20\t91\t话\n"
            "5\t1\t1\t1\t1\t7\t176\t30\t120\t20\t92\t13800138000\n"
            "5\t1\t1\t1\t1\t8\t326\t30\t18\t20\t91\t地\n"
            "5\t1\t1\t1\t1\t9\t348\t30\t18\t20\t91\t址\n"
            "5\t1\t1\t1\t1\t10\t376\t30\t220\t20\t90\t北京市朝阳区建国路88号\n"
        )
        completed = mock.Mock(returncode=0, stdout=tsv)

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+chi_sim"},
        ), mock.patch(
            "backend.lawdit.ocr_capabilities.shutil.which",
            return_value="/usr/bin/tesseract",
        ), mock.patch(
            "backend.lawdit.source_image_ocr.subprocess.run",
            return_value=completed,
        ):
            extracted = extract_document_content(body=b"image", content_type="image/png", name="cjk-badge.png")

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        address_signal = next(signal for signal in signals if signal["type"] == "address")
        region = address_signal["evidenceAnchor"]["selector"]["pageRegion"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.text, "姓名王芳电话13800138000地址北京市朝阳区建国路88号")
        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertEqual(region["x"], 376)
        self.assertEqual(region["origin"], "top_left")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)

    @unittest.skipUnless(Image is not None, "Pillow is unavailable for OCR preprocessing fixture generation.")
    def test_image_ocr_preprocesses_colored_overlay_text_without_raw_values(self) -> None:
        image = Image.new("RGB", (240, 120), "white")
        for x in range(40, 200):
            for y in range(30, 70):
                image.putpixel((x, y), (245, 70, 50))
        buffer = BytesIO()
        image.save(buffer, format="PNG")

        overlay_text = "姓名：王芳\n地址：北京市朝阳区建国路88号\nPassport: EN1234567"
        empty_tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        overlay_tsv = (
            empty_tsv
            + "1\t1\t0\t0\t0\t0\t0\t0\t240\t120\t-1\t\n"
            + "5\t1\t1\t1\t1\t1\t20\t20\t48\t18\t92\t姓名\n"
            + "5\t1\t1\t1\t1\t2\t72\t20\t36\t18\t92\t王芳\n"
            + "5\t1\t1\t1\t2\t1\t20\t48\t48\t18\t92\t地址\n"
            + "5\t1\t1\t1\t2\t2\t72\t48\t130\t18\t90\t北京市朝阳区建国路88号\n"
            + "5\t1\t1\t1\t3\t1\t20\t76\t70\t18\t91\tPassport:\n"
            + "5\t1\t1\t1\t3\t2\t96\t76\t90\t18\t91\tEN1234567\n"
        )

        def fake_tesseract(command: list[str], **kwargs: object) -> mock.Mock:
            image_path = command[1]
            stdout = overlay_tsv if "red_overlay" in image_path else empty_tsv
            return mock.Mock(returncode=0, stdout=stdout)

        with mock.patch.dict(
            "os.environ",
            {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+chi_sim"},
        ), mock.patch(
            "backend.lawdit.ocr_capabilities.shutil.which",
            return_value="/usr/bin/tesseract",
        ), mock.patch(
            "backend.lawdit.source_image_ocr.subprocess.run",
            side_effect=fake_tesseract,
        ) as run:
            extracted = extract_document_content(body=buffer.getvalue(), content_type="image/png", name="overlay.png")

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        passport_signal = next(signal for signal in signals if signal["type"] == "passport_number")
        selector = passport_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "address", "passport_number"}.issubset(signal_types))
        self.assertGreaterEqual(run.call_count, 2)
        self.assertEqual(selector["sourceStart"], extracted.text.index("EN1234567"))
        self.assertEqual(selector["pageRegion"]["origin"], "top_left")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("北京市朝阳区建国路88号", serialized)
        self.assertNotIn("EN1234567", serialized)

    def test_pdf_ocr_page_image_regions_enrich_page_anchors_without_raw_values(self) -> None:
        ocr_text = "Contact privacy.pdfocr@example.org"
        email_start = ocr_text.index("privacy.pdfocr@example.org")

        class EmptyPdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [mock.Mock(extract_text=lambda: "")]

        def fake_rasterize(command: list[str], **kwargs: object) -> mock.Mock:
            image_prefix = Path(command[-1])
            image_prefix.with_name("page-1.png").write_bytes(b"rasterized-page")
            return mock.Mock(returncode=0)

        image_result = ImageOcrResult(
            ocr_text,
            text_locations=({
                "format": "image_ocr",
                "label": "Image OCR text",
                "start": 0,
                "end": len(ocr_text),
                "regions": ({
                    "start": email_start,
                    "end": len(ocr_text),
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
        )

        with mock.patch.dict("os.environ", {"LAWDIT_OCR_MODE": "local"}), mock.patch(
            "backend.lawdit.source_pdf_text.pdftoppm_path",
            return_value="/usr/bin/pdftoppm",
        ), mock.patch(
            "backend.lawdit.source_pdf_text.subprocess.run",
            side_effect=fake_rasterize,
        ), mock.patch(
            "backend.lawdit.source_pdf_text.extract_image_content",
            return_value=image_result,
        ):
            extracted = extract_document_content(
                body=b"%PDF-1.7 image-only",
                content_type="application/pdf",
                name="scan.pdf",
                pdf_reader=EmptyPdfReader,
            )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        email_signal = next(signal for signal in signals if signal["type"] == "email")
        selector = email_signal["evidenceAnchor"]["selector"]
        region = selector["pageRegion"]
        serialized = json.dumps(signals)

        self.assertEqual(extracted.file_format, "pdf_ocr")
        self.assertEqual(selector["page"], 1)
        self.assertEqual(selector["sourceStart"], email_start)
        self.assertEqual(region["origin"], "top_left")
        self.assertEqual(region["unit"], "px")
        self.assertEqual(region["pageWidth"], 1654)
        self.assertEqual(email_signal["evidenceAnchor"]["format"], "pdf_ocr")
        self.assertEqual(email_signal["evidenceAnchor"]["fallback"]["label"], "Page 1")
        self.assertNotIn("privacy.pdfocr@example.org", serialized)


if __name__ == "__main__":
    unittest.main()
