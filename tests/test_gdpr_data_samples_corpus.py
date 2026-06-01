from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_format_recognition import DocumentExtractionIssue, extract_document_content


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:EMP|EE|E)-\d{3,8}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2}\d{8,12}\b"),
)


class GdprDataSamplesCorpusTests(unittest.TestCase):
    def test_corpus_scan_report_records_ocr_capability_boundary(self) -> None:
        report = _scan_report()
        capabilities = report["hostCapabilities"]
        image_challenge = next(result for result in report["results"] if result["role"] == "image_ocr_challenge")

        self.assertIn(capabilities["ocrMode"], {"local", "deferred"})
        self.assertIsInstance(capabilities["languagesConfigured"], list)
        self.assertIsInstance(capabilities["tesseractAvailable"], bool)
        self.assertIsInstance(capabilities["pdftoppmAvailable"], bool)
        self.assertIsInstance(capabilities["imageOcrAvailable"], bool)
        self.assertIsInstance(capabilities["pdfOcrAvailable"], bool)
        self.assertEqual(image_challenge["status"], "ocr_deferred")
        self.assertEqual(image_challenge["recognitionDifficulty"], "hard")

    def test_raw_corpus_manifest_locks_drive_coverage_and_hashes(self) -> None:
        drive_manifest = _drive_manifest()
        raw_manifest = _raw_manifest()
        expected_drive_ids = {entry["id"] for entry in drive_manifest["files"]}
        tracked_drive_ids = {entry["driveFileId"] for entry in raw_manifest["files"] if "driveFileId" in entry}

        self.assertEqual(raw_manifest["coverage"]["driveManifestFilesRepresented"], len(expected_drive_ids))
        self.assertEqual(expected_drive_ids, tracked_drive_ids)

        for entry in raw_manifest["files"]:
            with self.subTest(path=entry["relativePath"]):
                path = Path(entry["relativePath"])
                self.assertTrue(path.exists())
                body = path.read_bytes()
                self.assertEqual(entry["byteSize"], len(body))
                self.assertEqual(entry["sha256"], hashlib.sha256(body).hexdigest())

    def test_raw_pdf_corpus_extracts_text_layer_and_redacts_detected_signals(self) -> None:
        try:
            import pypdf  # noqa: F401
        except Exception as error:
            self.skipTest(f"pypdf is required for raw PDF corpus extraction: {error}")

        pdf_entries = [entry for entry in _raw_manifest()["files"] if entry["mimeType"] == "application/pdf"]
        example_signal_files = 0
        total_signals = 0

        self.assertEqual(len(pdf_entries), 16)
        for entry in pdf_entries:
            path = Path(entry["relativePath"])
            with self.subTest(path=path.name):
                try:
                    extracted = extract_document_content(
                        body=path.read_bytes(),
                        content_type="application/pdf",
                        name=path.name,
                    )
                except DocumentExtractionIssue as error:
                    self.fail(error.detail)

                signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
                serialized = json.dumps(signals, ensure_ascii=False)

                self.assertIn(extracted.file_format, {"pdf_text_layer", "pdf_mixed"})
                self.assertIn(extracted.extraction_method, {"pdf_text_layer", "pdf_text_layer_with_page_ocr"})
                self.assertIn(extracted.recognition_difficulty, {"moderate", "hard"})
                self.assertTrue(extracted.text.strip())
                self.assertTrue(extracted.text_locations)

                if "_Example_" in entry["originalName"]:
                    example_signal_files += 1
                    self.assertTrue(signals)
                    self.assertTrue(any(signal.get("evidenceAnchor", {}).get("selector", {}).get("page") for signal in signals))

                for pattern in RAW_VALUE_PATTERNS:
                    for raw_value in pattern.findall(extracted.text):
                        self.assertNotIn(raw_value, serialized)

                total_signals += len(signals)

        self.assertEqual(example_signal_files, 10)
        self.assertGreaterEqual(total_signals, 60)


def _drive_manifest() -> dict[str, object]:
    return json.loads((FIXTURE_DIR / "drive_manifest.json").read_text(encoding="utf-8"))


def _raw_manifest() -> dict[str, object]:
    return json.loads((FIXTURE_DIR / "raw_corpus_manifest.json").read_text(encoding="utf-8"))


def _scan_report() -> dict[str, object]:
    return json.loads((FIXTURE_DIR / "corpus_scan_report.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
