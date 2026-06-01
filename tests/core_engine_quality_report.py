from __future__ import annotations

import argparse
import json
import runpy
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
DEFAULT_OUTPUT = FIXTURE_DIR / "core_engine_quality_report.json"
GENERATED_HELPER_PATH = Path(__file__).with_name("test_generated_format_challenges.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a redacted core-engine quality report.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Report JSON output path.")
    args = parser.parse_args()

    output = Path(args.output)
    report = build_report(command=safe_command(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_report(*, command: str) -> dict[str, Any]:
    suites = [
        evaluate_core_multilingual_cases(),
        evaluate_generated_format_challenges(),
        evaluate_core_negative_cases(),
    ]
    totals = aggregate_suites(suites)
    return {
        "reportId": "core_engine_quality_2026-06-01_positive_negative_oracles",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "privacyRule": "This report stores case IDs, language/format labels, expected signal types, actual signal types, negative-case signal counts, and aggregate quality metrics only. It must not include raw source text, raw detected values, source bodies, provider tokens, Drive URLs, page images, or private absolute paths.",
        "command": command,
        "suites": suites,
        "totals": totals,
        "safetyChecks": {
            "rawTextPersisted": False,
            "rawDetectedValuesPersisted": False,
            "sourceBodiesPersisted": False,
            "privateAbsolutePathsPersisted": False,
            "providerTokensPersisted": False,
        },
    }


def evaluate_core_multilingual_cases() -> dict[str, Any]:
    payload = json.loads((FIXTURE_DIR / "core_multilingual_cases.json").read_text(encoding="utf-8"))
    cases = []
    for case in payload["cases"]:
        extracted = extract_document_content(
            body=str(case["text"]).encode("utf-8"),
            content_type="text/plain",
            name=f"{case['caseId']}.txt",
        )
        cases.append(_evaluate_case(
            suite="core_multilingual_cases",
            case_id=str(case["caseId"]),
            language=str(case["language"]),
            file_format=extracted.file_format,
            expected_types=tuple(str(signal_type) for signal_type in case["expectedTypes"]),
            extracted_text=extracted.text,
            text_locations=extracted.text_locations,
        ))
    return _suite_report("core_multilingual_cases", cases)


def evaluate_generated_format_challenges() -> dict[str, Any]:
    helpers = runpy.run_path(str(GENERATED_HELPER_PATH))
    challenge_cases = helpers["_challenge_cases"]()
    extract_case = helpers["_extract_case"]
    cases = []
    for case in challenge_cases:
        extracted = extract_case(case)
        cases.append(_evaluate_case(
            suite="generated_format_challenges",
            case_id=str(case["caseId"]),
            language=str(case.get("language") or "mixed"),
            file_format=str(case["expectedFormat"]),
            expected_types=tuple(str(signal_type) for signal_type in case["expectedTypes"]),
            extracted_text=extracted.text,
            text_locations=extracted.text_locations,
        ))
    return _suite_report("generated_format_challenges", cases)


def evaluate_core_negative_cases() -> dict[str, Any]:
    payload = json.loads((FIXTURE_DIR / "core_negative_cases.json").read_text(encoding="utf-8"))
    cases = []
    for case in payload["cases"]:
        extracted = extract_document_content(
            body=str(case["text"]).encode("utf-8"),
            content_type=str(case["contentType"]),
            name=str(case["fileName"]),
        )
        cases.append(_evaluate_case(
            suite="core_negative_cases",
            case_id=str(case["caseId"]),
            language=str(case["language"]),
            file_format=extracted.file_format,
            expected_types=tuple(str(signal_type) for signal_type in case.get("expectedTypes", ())),
            extracted_text=extracted.text,
            text_locations=extracted.text_locations,
        ))
    return _suite_report("core_negative_cases", cases)


def _evaluate_case(
    *,
    suite: str,
    case_id: str,
    language: str,
    file_format: str,
    expected_types: tuple[str, ...],
    extracted_text: str,
    text_locations: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    signals = apply_source_locations(detect_signals(extracted_text), text_locations)
    actual_types = tuple(sorted({str(signal.get("type") or "unknown") for signal in signals}))
    expected = tuple(sorted(set(expected_types)))
    matched = tuple(signal_type for signal_type in expected if signal_type in actual_types)
    false_negatives = tuple(signal_type for signal_type in expected if signal_type not in actual_types)
    false_positives = tuple(signal_type for signal_type in actual_types if signal_type not in expected)
    return {
        "suite": suite,
        "caseId": case_id,
        "language": language,
        "format": file_format,
        "expectedTypes": list(expected),
        "actualTypes": list(actual_types),
        "matchedTypes": list(matched),
        "falseNegativeTypes": list(false_negatives),
        "falsePositiveTypes": list(false_positives),
        "signalCount": len(signals),
        "perfectTypeMatch": not false_negatives and not false_positives,
    }


def _suite_report(name: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = metrics_for_cases(cases)
    languages = Counter(str(case["language"]) for case in cases)
    formats = Counter(str(case["format"]) for case in cases)
    expected_types = Counter(signal_type for case in cases for signal_type in case["expectedTypes"])
    actual_types = Counter(signal_type for case in cases for signal_type in case["actualTypes"])
    return {
        "name": name,
        "metrics": metrics,
        "languageCounts": dict(sorted(languages.items())),
        "formatCounts": dict(sorted(formats.items())),
        "expectedTypeCounts": dict(sorted(expected_types.items())),
        "actualTypeCounts": dict(sorted(actual_types.items())),
        "cases": cases,
    }


def aggregate_suites(suites: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [case for suite in suites for case in suite["cases"]]
    metrics = metrics_for_cases(cases)
    metrics["suiteCount"] = len(suites)
    return metrics


def metrics_for_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    expected_count = sum(len(case["expectedTypes"]) for case in cases)
    actual_count = sum(len(case["actualTypes"]) for case in cases)
    matched_count = sum(len(case["matchedTypes"]) for case in cases)
    false_negative_count = sum(len(case["falseNegativeTypes"]) for case in cases)
    false_positive_count = sum(len(case["falsePositiveTypes"]) for case in cases)
    precision = matched_count / actual_count if actual_count else 1.0
    recall = matched_count / expected_count if expected_count else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "caseCount": len(cases),
        "perfectCaseCount": sum(1 for case in cases if case["perfectTypeMatch"]),
        "expectedTypeAssertions": expected_count,
        "actualTypeAssertions": actual_count,
        "matchedTypeAssertions": matched_count,
        "falseNegativeTypeCount": false_negative_count,
        "falsePositiveTypeCount": false_positive_count,
        "typePrecision": round(precision, 6),
        "typeRecall": round(recall, 6),
        "typeF1": round(f1, 6),
    }


def safe_command(output: Path) -> str:
    try:
        display_output = output.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_output = output.name
    return f"python3 tests/core_engine_quality_report.py --output {display_output}"


if __name__ == "__main__":
    main()
