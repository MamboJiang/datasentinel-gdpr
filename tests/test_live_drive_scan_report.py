from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"https?://"),
    re.compile(r"/Users/[^\"\\s]+"),
    re.compile(r"/srv/lawdit/(?:sources|data)/[^\"\\s]+"),
    re.compile(r"\b(?:access_token|refresh_token|Bearer)\b"),
)


class LiveDriveScanReportTests(unittest.TestCase):
    def test_agent_us_live_drive_scan_report_records_server_scan_without_raw_values(self) -> None:
        report = json.loads((FIXTURE_DIR / "live_drive_scan_report_agent_us.json").read_text(encoding="utf-8"))
        serialized = json.dumps(report, ensure_ascii=False)

        self.assertTrue(report["bindingConnected"])
        self.assertEqual(report["sourceCreateStatusCode"], 201)
        self.assertEqual(report["scanStartStatusCode"], 202)
        self.assertEqual(report["scanStatus"], "completed")
        self.assertGreaterEqual(report["contentExtraction"]["processedFiles"], 18)
        self.assertEqual(report["contentExtraction"]["successfulFiles"], report["contentExtraction"]["processedFiles"])
        self.assertEqual(report["contentExtraction"]["unsupportedFiles"], 0)
        self.assertEqual(report["contentExtraction"]["ocrDeferredFiles"], 0)
        self.assertEqual(report["contentExtraction"]["rawContentExposed"], False)
        self.assertEqual(report["contentExtraction"]["modelCalls"], 0)
        self.assertNotIn("1 MB text extraction limit", serialized)
        self.assertIn(
            ("pdf_mixed", "pdf_text_layer_with_page_ocr"),
            {
                (item["format"], item["method"])
                for item in report["contentExtraction"]["formatCounts"]
            },
        )
        self.assertIn(
            ("text", "sniffed_unicode_text"),
            {
                (item["format"], item["method"])
                for item in report["contentExtraction"]["formatCounts"]
            },
        )
        self.assertIn("passport_number", {item["type"] for item in report["signalDetection"]["signalTypeCounts"]})
        self.assertGreater(report["signalDetection"]["detectedSignals"], 0)
        self.assertGreater(report["findingAssembly"]["assembledFindings"], 0)
        self.assertGreater(report["sourceReviewPreviewSampledFindings"], 0)
        self.assertEqual(report["sourceReviewPreviewSample"]["redactionMode"], "anchor_only")
        self.assertEqual(report["sourceReviewPreviewSample"]["rawContentExposed"], False)
        self.assertEqual(report["sourceReviewPreviewSample"]["pageImagesExposed"], False)
        self.assertEqual(report["mixedPdfPreviewSample"]["fileFormat"], "pdf_mixed")
        self.assertEqual(report["mixedPdfPreviewSample"]["extractionMethod"], "pdf_text_layer_with_page_ocr")
        self.assertIn("pdf_ocr", report["mixedPdfPreviewSample"]["anchorFormats"])
        self.assertIn("pdf_text_layer", report["mixedPdfPreviewSample"]["anchorFormats"])
        self.assertGreater(report["mixedPdfPreviewSample"]["pageRegionAnchorCount"], 0)
        self.assertEqual(report["mixedPdfPreviewSample"]["rawContentExposed"], False)
        self.assertEqual(report["mixedPdfPreviewSample"]["pageImagesExposed"], False)

        for key, value in report["safetyChecks"].items():
            self.assertFalse(value, key)
        for pattern in RAW_VALUE_PATTERNS:
            self.assertIsNone(pattern.search(serialized))


if __name__ == "__main__":
    unittest.main()
