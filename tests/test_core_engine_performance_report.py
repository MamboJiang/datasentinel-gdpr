from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
REPORTS = (
    FIXTURE_DIR / "core_engine_performance_report.json",
    FIXTURE_DIR / "core_engine_performance_report_agent_us.json",
)
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"/Users/[^\"\\s]+"),
    re.compile(r"/srv/datasentinel/(?:sources|data)/[^\"\\s]+"),
)


class CoreEnginePerformanceReportTests(unittest.TestCase):
    def test_performance_report_records_mixed_corpus_metrics_without_raw_values(self) -> None:
        for path in REPORTS:
            with self.subTest(report=path.name):
                report = json.loads(path.read_text(encoding="utf-8"))
                self.assert_common_report_contract(report)

    def test_agent_us_report_proves_server_local_ocr_capability(self) -> None:
        report = json.loads((FIXTURE_DIR / "core_engine_performance_report_agent_us.json").read_text(encoding="utf-8"))
        capabilities = report["ocrCapabilities"]

        self.assertIn("Linux", report["host"]["platform"])
        self.assertEqual(capabilities["ocrMode"], "local")
        self.assertTrue(capabilities["tesseractAvailable"])
        self.assertTrue(capabilities["pdftoppmAvailable"])
        self.assertTrue(capabilities["imageOcrAvailable"])
        self.assertTrue(capabilities["pdfOcrAvailable"])
        self.assertIn("chi_sim", capabilities["languagesConfigured"])
        self.assertIn("ara", capabilities["languagesConfigured"])
        self.assertGreaterEqual(report["totals"]["processedFiles"], 35)
        self.assertEqual(report["totals"]["ocrDeferredFiles"], 0)
        self.assertEqual(report["totals"]["unsupportedFiles"], 0)
        self.assertGreaterEqual(report["totals"]["formatCounts"]["image_ocr"], 2)

    def assert_common_report_contract(self, report: dict) -> None:
        serialized = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["safetyChecks"]["rawTextPersisted"], False)
        self.assertEqual(report["safetyChecks"]["rawDetectedValuesPersisted"], False)
        self.assertEqual(report["safetyChecks"]["sourceBodiesPersisted"], False)
        self.assertGreaterEqual(report["totals"]["processedFiles"], 30)
        self.assertGreater(report["totals"]["throughputFilesPerSecond"], 0)
        self.assertGreater(report["totals"]["peakRssMiB"], 0)
        self.assertEqual(report["totals"]["modelCalls"], 0)
        self.assertEqual(report["totals"]["estimatedCostUsd"], 0.0)
        self.assertIn("pdf_text_layer", report["totals"]["formatCounts"])
        self.assertIn("zip", report["totals"]["formatCounts"])
        self.assertIn("person_name", report["totals"]["signalTypeCounts"])
        self.assertTrue(report["command"].startswith("python3 tests/core_engine_performance_benchmark.py --output "))

        cap_suite = next(suite for suite in report["suites"] if suite["name"] == "large_signal_cap")
        self.assertEqual(cap_suite["maxSignalsInDocument"], report["limits"]["maxSignalsPerDocument"])
        self.assertTrue(cap_suite["signalCapEnforced"])

        for pattern in RAW_VALUE_PATTERNS:
            self.assertIsNone(pattern.search(serialized))


if __name__ == "__main__":
    unittest.main()
