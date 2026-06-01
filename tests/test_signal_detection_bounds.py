from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.lawdit.deterministic_signals import (
    MAX_SIGNAL_SCAN_CHARS,
    MAX_SIGNALS_PER_DOCUMENT,
    detect_signals,
)
from backend.lawdit.source_documents import read_source_documents


class SignalDetectionBoundsTests(unittest.TestCase):
    def test_detection_caps_signals_per_document_without_raw_values(self) -> None:
        text = "\n".join(
            f"Name {index}: Person{index:03d} Example"
            for index in range(MAX_SIGNALS_PER_DOCUMENT + 8)
        )

        signals = detect_signals(text)
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(len(signals), MAX_SIGNALS_PER_DOCUMENT)
        self.assertIn("Name 31: [REDACTED_PERSON_NAME]", serialized)
        self.assertNotIn("Name 32", serialized)
        self.assertNotIn("Person000", serialized)
        self.assertNotIn("Person031", serialized)

    def test_detection_ignores_content_past_scan_character_limit(self) -> None:
        tail_email = "after.boundary@example.invalid"
        text = ("x" * MAX_SIGNAL_SCAN_CHARS) + f"\nEmail: {tail_email}"

        signals = detect_signals(text)

        self.assertEqual(signals, [])

    def test_local_source_reader_reports_file_count_limit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(5):
                (root / f"case_{index}.txt").write_text(f"Name: Person {index}\n", encoding="utf-8")

            with mock.patch("backend.lawdit.source_documents.MAX_SOURCE_FILES", 3):
                batch = read_source_documents({
                    "sourceId": "source_limit",
                    "sourceType": "local_repo",
                    "config": {"rootPath": str(root)},
                }, {})

        self.assertEqual(batch.total_files, 5)
        self.assertEqual(len(batch.documents), 3)
        self.assertEqual(batch.unsupported_files, 0)
        self.assertIn("Local source scan stopped at the prelaunch 3 file limit.", batch.warnings)


if __name__ == "__main__":
    unittest.main()
