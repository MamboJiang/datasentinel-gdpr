from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
REPORT_PATH = FIXTURE_DIR / "engine_hardening_validation_report.json"
LIVE_DRIVE_REPORT_PATH = FIXTURE_DIR / "live_drive_scan_report_agent_us.json"
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"/Users/[^\"\\s]+"),
    re.compile(r"/srv/lawdit/(?:sources|data)/[^\"\\s]+"),
    re.compile(r"https://drive\\.google\\.com/[^\"\\s]+"),
)


class EngineHardeningValidationReportTests(unittest.TestCase):
    def test_validation_report_tracks_current_deployment_evidence(self) -> None:
        report = _load(REPORT_PATH)
        deployment = report["agentUsDeployment"]

        self.assertTrue(deployment["appRelease"].endswith("20260601065039-ocr-profile-stale-route"))
        self.assertTrue(deployment["frontendRelease"].endswith("20260601065039-ocr-profile-stale-route"))
        self.assertEqual(deployment["remoteBackendTests"]["testCount"], 172)
        self.assertEqual(deployment["remoteRiskTaxonomyTests"]["result"], "passed")
        self.assertEqual(report["localValidation"]["backendTests"]["testCount"], 170)
        self.assertEqual(report["localValidation"]["frontendTests"]["testCount"], 82)

    def test_validation_report_keeps_supported_formats_and_live_drive_counts_fresh(self) -> None:
        report = _load(REPORT_PATH)
        live = _load(LIVE_DRIVE_REPORT_PATH)

        self.assertEqual(len(report["supportedFormatsValidatedInUi"]), 30)
        self.assertIn("Suffixless text/config", report["supportedFormatsValidatedInUi"])
        self.assertIn("MP4/MOV/M4V/MKV/WEBM/AVI video frame OCR", report["supportedFormatsValidatedInUi"])
        self.assertEqual(report["liveDriveScan"]["processedFiles"], live["contentExtraction"]["processedFiles"])
        self.assertEqual(report["liveDriveScan"]["successfulFiles"], live["contentExtraction"]["successfulFiles"])
        self.assertEqual(report["liveDriveScan"]["unsupportedFiles"], live["contentExtraction"]["unsupportedFiles"])
        self.assertEqual(report["liveDriveScan"]["ocrDeferredFiles"], live["contentExtraction"]["ocrDeferredFiles"])
        self.assertEqual(report["liveDriveScan"]["assembledFindings"], live["findingAssembly"]["assembledFindings"])

    def test_validation_report_does_not_persist_raw_values_or_private_paths(self) -> None:
        serialized = json.dumps(_load(REPORT_PATH), ensure_ascii=False)

        self.assertNotIn("stacked-ocr-labels", serialized)
        self.assertNotIn("extensionless-text-final", serialized)
        for pattern in RAW_VALUE_PATTERNS:
            self.assertIsNone(pattern.search(serialized))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
