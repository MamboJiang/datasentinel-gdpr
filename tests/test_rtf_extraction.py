from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_documents import read_source_documents
from backend.datasentinel.source_format_recognition import extract_document_content


class RtfExtractionTests(unittest.TestCase):
    def test_rtf_unicode_and_hex_text_scans_with_source_anchor_without_raw_values(self) -> None:
        body = (
            r"{\rtf1\ansi{\fonttbl{\f0 Arial;}}"
            r"\u22995?\u21517?: \u29579?\u33459?\par "
            r"T\'e9l\'e9phone: +33123456789}"
        ).encode("latin-1")

        extracted = extract_document_content(body=body, content_type="application/rtf", name="contact.rtf")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        selector = name_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "rtf")
        self.assertEqual(extracted.extraction_method, "rtf_text")
        self.assertTrue({"person_name", "phone_number"}.issubset(signal_types))
        self.assertEqual(selector["type"], "textPosition")
        self.assertEqual(name_signal["evidenceAnchor"]["format"], "rtf")
        self.assertIn("sourceStart", selector)
        self.assertIn("sourceEnd", selector)
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("+33123456789", serialized)

    def test_local_source_accepts_rtf_suffix(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contact.rtf").write_bytes(
                b"{\\rtf1\\ansi Name: Claire Martin\\par Phone: +33123456789}"
            )

            batch = read_source_documents({
                "sourceId": "source_rtf",
                "sourceType": "local_repo",
                "config": {"rootPath": str(root)},
            }, {})

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.total_files, 1)
        self.assertEqual(batch.documents[0].file_format, "rtf")
        self.assertEqual(batch.documents[0].extraction_method, "rtf_text")


if __name__ == "__main__":
    unittest.main()
