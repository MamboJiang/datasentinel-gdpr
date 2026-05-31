from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_documents import read_source_documents
from backend.datasentinel.source_format_recognition import extract_document_content


class EmailExtractionTests(unittest.TestCase):
    def test_eml_headers_and_plain_body_get_structure_path_anchors(self) -> None:
        body = _email_bytes(
            headers=(
                "From: Privacy Reviewer <reviewer@example.org>",
                "To: archive@example.org",
                "Subject: GDPR sample message",
                "Content-Type: text/plain; charset=utf-8",
            ),
            body="姓名：王芳\n电话：13800138000\n",
        )

        extracted = extract_document_content(body=body, content_type="message/rfc822", name="chinese_contact.eml")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "eml")
        self.assertEqual(extracted.extraction_method, "rfc5322_mime_text")
        self.assertEqual(extracted.recognition_difficulty, "moderate")
        self.assertTrue(all(selector["type"] == "structurePath" for selector in selectors))
        self.assertTrue(any(selector["partName"] == "body" for selector in selectors))
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)

    def test_multipart_email_extracts_html_text_and_skips_attachments(self) -> None:
        body = b"""From: sender@example.org
To: privacy@example.org
Subject: Arabic contact
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="outer"

--outer
Content-Type: text/html; charset=utf-8

<p>\xd8\xa7\xd9\x84\xd8\xa7\xd8\xb3\xd9\x85: \xd9\x84\xd9\x8a\xd9\x84\xd9\x89 \xd8\xad\xd8\xb3\xd9\x86</p><p>\xd8\xa7\xd9\x84\xd9\x87\xd8\xa7\xd8\xaa\xd9\x81: +971 501234567</p>
--outer
Content-Type: text/plain; charset=utf-8; name="hidden.txt"

\xec\xa0\x84\xed\x99\x94: Should Not Extract Either
--outer
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="\xd9\x84\xd9\x8a\xd9\x84\xd9\x89.txt"

\xd8\xa7\xd9\x84\xd8\xa7\xd8\xb3\xd9\x85: Should Not Extract
--outer--
"""

        extracted = extract_document_content(body=body, content_type="message/rfc822", name="arabic_contact.eml")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "phone_number"}.issubset(signal_types))
        self.assertIn("Email body part 1", serialized)
        self.assertNotIn("ليلى حسن", serialized)
        self.assertNotIn("Should Not Extract", extracted.text)
        self.assertNotIn("Should Not Extract Either", extracted.text)
        self.assertNotIn("ليلى.txt", serialized)

    def test_local_source_accepts_eml_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "message.eml").write_bytes(_email_bytes(
                headers=("From: reviewer@example.org", "Content-Type: text/plain; charset=utf-8"),
                body="Nombre: Laura Garcia\n",
            ))

            batch = read_source_documents(
                {"sourceType": "local_repo", "config": {"rootPath": str(root)}},
                {},
            )

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.documents[0].file_format, "eml")
        self.assertEqual(batch.documents[0].recognition_difficulty, "moderate")


def _email_bytes(*, headers: tuple[str, ...], body: str) -> bytes:
    return ("\n".join(headers) + "\n\n" + body).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
