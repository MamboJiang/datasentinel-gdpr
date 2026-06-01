from __future__ import annotations

import json
import re
import runpy
import unittest
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
REPORT_PATH = FIXTURE_DIR / "core_engine_quality_report.json"
REPORT_SCRIPT = Path(__file__).with_name("core_engine_quality_report.py")
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"/Users/[^\"\\s]+"),
    re.compile(r"/srv/datasentinel/(?:sources|data)/[^\"\\s]+"),
)


class CoreEngineQualityReportTests(unittest.TestCase):
    def test_quality_report_records_precision_recall_without_raw_values(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

        self.assert_report_contract(report)

    def test_quality_report_fixture_matches_current_detector_outputs(self) -> None:
        fixture = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        build_report = runpy.run_path(str(REPORT_SCRIPT))["build_report"]
        current = build_report(command=fixture["command"])

        self.assertEqual(current["totals"], fixture["totals"])
        self.assertEqual(
            [(suite["name"], suite["metrics"]) for suite in current["suites"]],
            [(suite["name"], suite["metrics"]) for suite in fixture["suites"]],
        )
        self.assertEqual(
            [
                (case["caseId"], case["actualTypes"], case["falseNegativeTypes"], case["falsePositiveTypes"])
                for suite in current["suites"]
                for case in suite["cases"]
            ],
            [
                (case["caseId"], case["actualTypes"], case["falseNegativeTypes"], case["falsePositiveTypes"])
                for suite in fixture["suites"]
                for case in suite["cases"]
            ],
        )

    def test_quality_report_does_not_persist_fixture_raw_values(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        serialized = json.dumps(report, ensure_ascii=False)
        forbidden_values = _forbidden_values()

        for raw_value in forbidden_values:
            self.assertNotIn(raw_value, serialized)
        for pattern in RAW_VALUE_PATTERNS:
            self.assertIsNone(pattern.search(serialized))

    def assert_report_contract(self, report: dict) -> None:
        self.assertEqual(report["safetyChecks"]["rawTextPersisted"], False)
        self.assertEqual(report["safetyChecks"]["rawDetectedValuesPersisted"], False)
        self.assertEqual(report["safetyChecks"]["sourceBodiesPersisted"], False)
        self.assertGreaterEqual(report["totals"]["caseCount"], 25)
        self.assertGreaterEqual(report["totals"]["expectedTypeAssertions"], 100)
        self.assertEqual(report["totals"]["falseNegativeTypeCount"], 0)
        self.assertEqual(report["totals"]["falsePositiveTypeCount"], 0)
        self.assertEqual(report["totals"]["typePrecision"], 1.0)
        self.assertEqual(report["totals"]["typeRecall"], 1.0)
        self.assertEqual(report["totals"]["typeF1"], 1.0)
        self.assertTrue(report["command"].startswith("python3 tests/core_engine_quality_report.py --output "))
        self.assertEqual({suite["name"] for suite in report["suites"]}, {"core_multilingual_cases", "generated_format_challenges"})


def _forbidden_values() -> list[str]:
    core_cases = json.loads((FIXTURE_DIR / "core_multilingual_cases.json").read_text(encoding="utf-8"))["cases"]
    generated_cases = json.loads((FIXTURE_DIR / "generated_format_challenges.json").read_text(encoding="utf-8"))["cases"]
    values = []
    for case in [*core_cases, *generated_cases]:
        values.extend(str(value) for value in case["forbiddenValues"])
    return values


if __name__ == "__main__":
    unittest.main()
