from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_documents import read_source_documents
from backend.lawdit.source_format_recognition import extract_document_content


class JsonStructureAnchorTests(unittest.TestCase):
    def test_jsonl_signals_use_structure_paths_without_raw_values(self) -> None:
        body = (
            '{"contact":{"姓名":"王芳","电话":"13800138000"}}\n'
            '{"contact":{"Correo electrónico":"privacidad.jsonl@example.org"}}\n'
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="application/x-ndjson", name="contacts.jsonl")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        selector = name_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "jsonl")
        self.assertEqual(extracted.extraction_method, "json_structure_text")
        self.assertTrue({"person_name", "phone_number", "email"}.issubset(signal_types))
        self.assertEqual(selector["type"], "structurePath")
        self.assertEqual(selector["recordIndex"], 1)
        self.assertEqual(selector["lineNumber"], 1)
        self.assertEqual(selector["fieldIndex"], 1)
        self.assertEqual(selector["blockLabel"], "JSONL record 1 field 1.1")
        self.assertEqual(selector["path"], "/record[1]/field[1]/field[1]")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("13800138000", serialized)
        self.assertNotIn("privacidad.jsonl@example.org", serialized)

    def test_local_source_accepts_jsonl_ndjson_and_htm_suffixes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "events.jsonl").write_text('{"姓名":"王芳"}\n', encoding="utf-8")
            (root / "events.ndjson").write_text('{"Téléphone":"+33123456789"}\n', encoding="utf-8")
            (root / "profile.htm").write_text("<p>Name: Claire Martin</p>", encoding="utf-8")

            batch = read_source_documents({
                "sourceId": "source_json_suffixes",
                "sourceType": "local_repo",
                "config": {"rootPath": str(root)},
            }, {})

        formats = {document.file_format for document in batch.documents}
        serialized_locations = json.dumps([
            location
            for document in batch.documents
            for location in document.text_locations
        ], ensure_ascii=False)

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.total_files, 3)
        self.assertEqual(len(batch.documents), 3)
        self.assertTrue({"jsonl", "ndjson", "html"}.issubset(formats))
        self.assertIn('"type": "structurePath"', serialized_locations)
        self.assertNotIn("王芳", serialized_locations)
        self.assertNotIn("Claire Martin", serialized_locations)


if __name__ == "__main__":
    unittest.main()
