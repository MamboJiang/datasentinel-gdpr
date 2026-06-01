from __future__ import annotations

import json
import unittest

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content


class TextDecodingTests(unittest.TestCase):
    def test_charset_declared_utf16le_text_scans_multilingual_labels(self) -> None:
        text = "姓名：王芳\n电话：13800138000\n"
        extracted = extract_document_content(
            body=text.encode("utf-16-le"),
            content_type="text/plain; charset=utf-16le",
            name="contact.txt",
        )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "txt")
        self.assertTrue({"person_name", "phone_number"}.issubset({signal["type"] for signal in signals}))
        self.assertTrue(all(signal["evidenceAnchor"]["selector"]["type"] == "textPosition" for signal in signals))
        name_selector = next(signal["evidenceAnchor"]["selector"] for signal in signals if signal["type"] == "person_name")
        phone_selector = next(signal["evidenceAnchor"]["selector"] for signal in signals if signal["type"] == "phone_number")
        self.assertEqual(name_selector["sourceStart"], text.index("王芳"))
        self.assertEqual(name_selector["lineNumber"], 1)
        self.assertEqual(name_selector["columnNumber"], 4)
        self.assertEqual(phone_selector["lineNumber"], 2)
        self.assertEqual(phone_selector["columnNumber"], 4)
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)

    def test_charset_declared_utf16le_csv_keeps_table_cell_anchors(self) -> None:
        text = "field,value\nNombre,Laura Garcia\nTeléfono,+34123456789\n"
        extracted = extract_document_content(
            body=text.encode("utf-16-le"),
            content_type="text/csv; charset=utf-16le",
            name="contacts.csv",
        )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "csv")
        self.assertTrue({"person_name", "phone_number"}.issubset({signal["type"] for signal in signals}))
        self.assertTrue(all(selector["type"] == "tableCell" for selector in selectors))
        self.assertNotIn("Laura Garcia", serialized)
        self.assertNotIn("+34123456789", serialized)

    def test_charset_declared_utf16le_json_keeps_structure_path_anchors(self) -> None:
        text = json.dumps({"姓名": "王芳", "电话": "13800138000"}, ensure_ascii=False)
        extracted = extract_document_content(
            body=text.encode("utf-16-le"),
            content_type="application/json; charset=utf-16le",
            name="contact.json",
        )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "json")
        self.assertTrue({"person_name", "phone_number"}.issubset({signal["type"] for signal in signals}))
        self.assertTrue(all(selector["type"] == "structurePath" for selector in selectors))
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)

    def test_charset_declared_utf16le_html_keeps_structure_path_anchors(self) -> None:
        text = "<section><p>姓名：王芳</p><p>电话：13800138000</p></section>"
        extracted = extract_document_content(
            body=text.encode("utf-16-le"),
            content_type="text/html; charset=utf-16le",
            name="contact.html",
        )

        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "html")
        self.assertTrue({"person_name", "phone_number"}.issubset({signal["type"] for signal in signals}))
        self.assertTrue(all(selector["type"] == "structurePath" for selector in selectors))
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)


if __name__ == "__main__":
    unittest.main()
