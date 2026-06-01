from __future__ import annotations

import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock
from xml.sax.saxutils import escape
from zipfile import ZipFile

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content
from backend.lawdit.source_image_ocr import ImageOcrResult
from backend.lawdit.source_pdf_text import PdfExtractionResult


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"


class GeneratedFormatChallengeTests(unittest.TestCase):
    def test_generated_multiformat_challenges_scan_with_redacted_source_anchors(self) -> None:
        cases = _challenge_cases()

        self.assertGreaterEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case["caseId"]):
                extracted = _extract_case(case)
                signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
                signal_types = {signal["type"] for signal in signals}
                serialized = json.dumps(signals, ensure_ascii=False)

                self.assertEqual(extracted.file_format, case["expectedFormat"])
                self.assertEqual(extracted.recognition_difficulty, case["expectedDifficulty"])
                self.assertTrue(set(case["expectedTypes"]).issubset(signal_types))
                self.assertTrue(extracted.text_locations)
                self.assertTrue(all(_has_source_anchor(signal, case["expectedFormat"]) for signal in signals))
                self.assertIn("[REDACTED_", serialized)
                for raw_value in case["forbiddenValues"]:
                    self.assertNotIn(raw_value, serialized)


def _challenge_cases() -> list[dict[str, object]]:
    payload = json.loads((FIXTURE_DIR / "generated_format_challenges.json").read_text(encoding="utf-8"))
    return list(payload["cases"])


def _extract_case(case: dict[str, object]):
    file_kind = str(case["fileKind"])
    text = str(case["text"])
    name = str(case["fileName"])
    content_type = str(case["contentType"])

    if file_kind == "docx":
        body = _docx_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "xlsx":
        body = _xlsx_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "pptx":
        body = _pptx_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "odt":
        body = _odt_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "ods":
        body = _ods_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "odp":
        body = _odp_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "eml":
        body = _eml_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "zip":
        body = _zip_challenge_bytes(text)
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "utf16_text":
        body = text.encode("utf-16-le")
        return extract_document_content(body=body, content_type=content_type, name=name)
    if file_kind == "image_ocr":
        with mock.patch(
            "backend.lawdit.source_format_recognition.extract_image_content",
            return_value=ImageOcrResult(
                text,
                text_locations=({"format": "image_ocr", "label": "Image OCR text", "start": 0, "end": len(text)},),
            ),
        ):
            return extract_document_content(body=b"synthetic-image", content_type=content_type, name=name)
    if file_kind == "pdf_ocr":
        with mock.patch(
            "backend.lawdit.source_pdf_text._ocr_result",
            return_value=PdfExtractionResult(
                text,
                "pdf_ocr",
                "pdf_page_image_ocr",
                "hard",
                text_locations=({"format": "pdf_ocr", "label": "Page 1", "start": 0, "end": len(text), "page": 1},),
            ),
        ):
            return extract_document_content(body=b"%PDF-1.7 image-only", content_type=content_type, name=name, pdf_reader=_EmptyPdfReader)
    return extract_document_content(body=text.encode("utf-8"), content_type=content_type, name=name)


def _has_source_anchor(signal: dict[str, object], expected_format: object) -> bool:
    anchor = signal.get("evidenceAnchor")
    if not isinstance(anchor, dict) or anchor.get("format") != expected_format:
        return False
    selector = anchor.get("selector")
    if not isinstance(selector, dict) or "sourceStart" not in selector or "sourceEnd" not in selector:
        return False
    if expected_format in {"csv", "xlsx", "ods"}:
        return selector.get("type") == "tableCell" and "row" in selector and "column" in selector
    if expected_format in {"docx", "pptx", "html", "xml", "json", "jsonl", "ndjson", "odt", "odp", "eml"}:
        return selector.get("type") == "structurePath" and "path" in selector
    if expected_format == "zip":
        return selector.get("containerType") == "zip" and "memberIndex" in selector
    return selector.get("type") == "textPosition"


def _docx_bytes(text: str) -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p></w:body>
</w:document>"""
    return _zip_bytes({"word/document.xml": xml})


def _xlsx_bytes(text: str) -> bytes:
    shared = f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>{escape(text)}</t></si>
</sst>"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData>
</worksheet>"""
    return _zip_bytes({"xl/sharedStrings.xml": shared, "xl/worksheets/sheet1.xml": sheet})


def _pptx_bytes(text: str) -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>"""
    return _zip_bytes({"ppt/slides/slide1.xml": xml})


def _odt_bytes(text: str) -> bytes:
    return _odf_bytes(f"<office:text>{_odf_paragraphs(text)}</office:text>")


def _ods_bytes(text: str) -> bytes:
    rows = "\n".join(_ods_row(line) for line in text.splitlines() if line.strip())
    return _odf_bytes(f"<office:spreadsheet><table:table>{rows}</table:table></office:spreadsheet>")


def _odp_bytes(text: str) -> bytes:
    return _odf_bytes(
        f"<office:presentation><draw:page><draw:frame><draw:text-box>{_odf_paragraphs(text)}</draw:text-box></draw:frame></draw:page></office:presentation>"
    )


def _odf_paragraphs(text: str) -> str:
    return "".join(f"<text:p>{escape(line)}</text:p>" for line in text.splitlines() if line.strip())


def _ods_row(line: str) -> str:
    label, separator, value = line.partition(":")
    if not separator:
        label, separator, value = line.partition("：")
    cells = (label.strip(), value.strip()) if separator else (line.strip(),)
    return "<table:table-row>" + "".join(f"<table:table-cell><text:p>{escape(cell)}</text:p></table:table-cell>" for cell in cells) + "</table:table-row>"


def _odf_bytes(inner_body: str) -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0">
  <office:body>{inner_body}</office:body>
</office:document-content>"""
    return _zip_bytes({"mimetype": "application/vnd.oasis.opendocument", "content.xml": xml})


def _eml_bytes(text: str) -> bytes:
    body = "\n".join(line for line in text.splitlines() if line.strip())
    return (
        "From: reviewer@example.org\n"
        "To: archive@example.org\n"
        "Subject: Generated privacy sample\n"
        "Content-Type: text/plain; charset=utf-8\n\n"
        f"{body}\n"
    ).encode("utf-8")


def _zip_challenge_bytes(text: str) -> bytes:
    lines = [line for line in text.splitlines() if line.strip()]
    csv_text = "field,value\n" + "\n".join(line.replace(",", ",", 1) for line in lines[:2])
    txt_text = "\n".join(lines[2:]) + "\n"
    return _zip_bytes({
        "Laura Garcia payroll.csv": csv_text,
        "nested/王芳 contact.txt": txt_text,
        "nested.zip": "not scanned",
    })


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)
    return buffer.getvalue()


class _EmptyPdfReader:
    def __init__(self, stream: object, strict: bool = False) -> None:
        self.pages = [mock.Mock(extract_text=lambda: "")]


if __name__ == "__main__":
    unittest.main()
