from __future__ import annotations

import json
import unittest

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content


class MarkdownExtractionTests(unittest.TestCase):
    def test_markdown_table_headers_create_multilingual_table_cell_anchors(self) -> None:
        body = (
            "# Access review\n\n"
            "| 姓名 | 电话 | 地址 |\n"
            "| --- | --- | --- |\n"
            "| 王芳 | 13800138000 | 北京市朝阳区示例路18号 |\n"
        ).encode("utf-8")

        extracted = extract_document_content(
            body=body,
            content_type="text/markdown",
            name="review.md",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        phone_signal = next(signal for signal in signals if signal["type"] == "phone_number")
        address_signal = next(signal for signal in signals if signal["type"] == "address")

        self.assertEqual(extracted.file_format, "markdown")
        self.assertEqual(extracted.extraction_method, "markdown_text")
        self.assertTrue({"person_name", "phone_number", "address"}.issubset(signal_types))
        self.assertEqual(name_signal["evidenceAnchor"]["format"], "markdown")
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "row 5 column A")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["type"], "tableCell")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["row"], 5)
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["columnLabel"], "A")
        self.assertEqual(phone_signal["evidenceAnchor"]["selector"]["columnLabel"], "B")
        self.assertEqual(address_signal["evidenceAnchor"]["selector"]["columnLabel"], "C")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("北京市朝阳区", serialized)

    def test_markdown_non_table_text_keeps_redacted_text_position_anchors(self) -> None:
        body = "## Intake\n\nName: Alice Example\nEmail: alice.markdown@example.org\n".encode("utf-8")

        extracted = extract_document_content(
            body=body,
            content_type="text/markdown",
            name="intake.md",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        serialized = json.dumps(signals)

        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        email_signal = next(signal for signal in signals if signal["type"] == "email")

        self.assertEqual(name_signal["evidenceAnchor"]["format"], "markdown")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["type"], "textPosition")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["lineNumber"], 3)
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["columnNumber"], 7)
        self.assertEqual(email_signal["evidenceAnchor"]["format"], "markdown")
        self.assertEqual(email_signal["evidenceAnchor"]["selector"]["lineNumber"], 4)
        self.assertEqual(email_signal["evidenceAnchor"]["selector"]["columnNumber"], 8)
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("alice.markdown@example.org", serialized)


if __name__ == "__main__":
    unittest.main()
