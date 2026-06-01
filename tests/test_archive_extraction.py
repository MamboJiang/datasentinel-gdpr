from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_documents import read_source_documents
from backend.lawdit.source_format_recognition import DocumentExtractionIssue, extract_document_content


class ArchiveExtractionTests(unittest.TestCase):
    def test_zip_members_scan_with_member_ordinal_anchors(self) -> None:
        body = _zip_bytes({
            "Laura Garcia payroll.csv": "field,value\nNombre,Laura Garcia\nTeléfono,+34123456789\n",
            "nested/王芳 contact.txt": "姓名：王芳\n电话：13800138000\n",
            "nested/archive.zip": "not scanned",
        })

        extracted = extract_document_content(body=body, content_type="application/zip", name="bundle.zip")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        serialized = json.dumps(signals, ensure_ascii=False)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]

        self.assertEqual(extracted.file_format, "zip")
        self.assertEqual(extracted.extraction_method, "zip_member_text")
        self.assertEqual(extracted.recognition_difficulty, "moderate")
        self.assertTrue(all(signal["evidenceAnchor"]["format"] == "zip" for signal in signals))
        self.assertTrue(all(selector["containerType"] == "zip" for selector in selectors))
        self.assertTrue(all("memberIndex" in selector for selector in selectors))
        self.assertTrue(any(selector["type"] == "tableCell" for selector in selectors))
        self.assertTrue(any(selector["type"] == "structurePath" for selector in selectors))
        self.assertNotIn("Laura Garcia payroll.csv", serialized)
        self.assertNotIn("王芳 contact.txt", serialized)
        self.assertNotIn("Laura Garcia", serialized)
        self.assertNotIn("王芳", serialized)

    def test_zip_with_no_extractable_members_is_recoverable_issue(self) -> None:
        body = _zip_bytes({
            "nested.zip": "not scanned",
            "binary.bin": "\x00\x01",
        })

        with self.assertRaises(DocumentExtractionIssue) as raised:
            extract_document_content(body=body, content_type="application/zip", name="empty.zip")

        self.assertEqual(raised.exception.recognition_difficulty, "hard")

    def test_local_source_accepts_zip_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bundle.zip").write_bytes(_zip_bytes({
                "contact.csv": "field,value\nNombre,Laura Garcia\n",
            }))

            batch = read_source_documents(
                {"sourceType": "local_repo", "config": {"rootPath": str(root)}},
                {},
            )

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.documents[0].file_format, "zip")
        self.assertEqual(batch.documents[0].recognition_difficulty, "moderate")


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
