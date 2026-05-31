from __future__ import annotations

import argparse
import json
import platform
import resource
import runpy
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.datasentinel.deterministic_signals import (
    MAX_SIGNAL_SCAN_CHARS,
    MAX_SIGNALS_PER_DOCUMENT,
    detect_signals,
)
from backend.datasentinel.ocr_capabilities import ocr_capabilities
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_documents import MAX_DOCUMENT_BYTES, MAX_SOURCE_FILES
from backend.datasentinel.source_format_recognition import DocumentExtractionIssue, extract_document_content

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gdpr_data_samples_main"
DEFAULT_OUTPUT = FIXTURE_DIR / "core_engine_performance_report.json"
HELPER_PATH = Path(__file__).with_name("test_generated_format_challenges.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a redacted core-engine performance benchmark report.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Report JSON output path.")
    args = parser.parse_args()

    output = Path(args.output)
    report = build_report(command=safe_command(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_report(*, command: str) -> dict[str, Any]:
    host = host_report()
    limits = {
        "maxDocumentBytes": MAX_DOCUMENT_BYTES,
        "maxSourceFiles": MAX_SOURCE_FILES,
        "maxSignalScanChars": MAX_SIGNAL_SCAN_CHARS,
        "maxSignalsPerDocument": MAX_SIGNALS_PER_DOCUMENT,
    }
    suites = [
        benchmark_generated_challenges(),
        benchmark_raw_corpus(),
        benchmark_large_signal_cap(),
    ]
    totals = aggregate_suites(suites)
    return {
        "reportId": "core_engine_performance_2026-05-31_mixed_corpus",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "privacyRule": "This benchmark records aggregate counts, timings, formats, signal types, and resource usage only. It must not include raw extracted text, raw detected values, provider tokens, source bodies, Drive URLs, or private absolute paths.",
        "command": command,
        "host": host,
        "limits": limits,
        "ocrCapabilities": ocr_capabilities(),
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


def benchmark_generated_challenges() -> dict[str, Any]:
    helpers = runpy.run_path(str(HELPER_PATH))
    cases = helpers["_challenge_cases"]()
    extract_case = helpers["_extract_case"]

    accumulator = SuiteAccumulator("generated_format_challenges")
    accumulator.note = "Uses generated multilingual challenge cases; image/PDF OCR challenge entries use the deterministic test helper's mocked OCR text to isolate parser/detector throughput."
    start = time.perf_counter()
    for case in cases:
        try:
            extracted = extract_case(case)
        except Exception:
            accumulator.unsupported_files += 1
            continue
        accumulator.record_extracted(extracted, body_size=len(str(case.get("text", "")).encode("utf-8")))
    accumulator.duration_seconds = time.perf_counter() - start
    return accumulator.to_report()


def benchmark_raw_corpus() -> dict[str, Any]:
    manifest = json.loads((FIXTURE_DIR / "raw_corpus_manifest.json").read_text(encoding="utf-8"))
    accumulator = SuiteAccumulator("raw_drive_corpus")
    accumulator.note = "Uses immutable local raw corpus copies represented by the Drive manifest; source metadata files are skipped."
    start = time.perf_counter()
    for entry in manifest["files"]:
        if entry.get("role") == "source_repo_metadata":
            accumulator.skipped_files += 1
            continue
        relative_path = entry["relativePath"]
        path = Path(relative_path)
        body = path.read_bytes()
        try:
            extracted = extract_document_content(
                body=body,
                content_type=str(entry.get("mimeType") or ""),
                name=path.name,
            )
        except DocumentExtractionIssue as issue:
            accumulator.unsupported_files += 1
            if issue.ocr_deferred:
                accumulator.ocr_deferred_files += 1
            accumulator.failure_difficulties[issue.recognition_difficulty] += 1
            continue
        accumulator.record_extracted(extracted, body_size=len(body))
    accumulator.duration_seconds = time.perf_counter() - start
    return accumulator.to_report()


def benchmark_large_signal_cap() -> dict[str, Any]:
    capped_lines = [
        f"Name {index}: Person{index:03d} Example"
        for index in range(MAX_SIGNALS_PER_DOCUMENT + 256)
    ]
    text = "\n".join(capped_lines) + "\n" + ("x" * MAX_SIGNAL_SCAN_CHARS)
    accumulator = SuiteAccumulator("large_signal_cap")
    accumulator.note = "Uses an in-memory oversized text stream to verify scan-window and per-document signal caps under load."
    start = time.perf_counter()
    signals = detect_signals(text)
    accumulator.duration_seconds = time.perf_counter() - start
    accumulator.processed_files = 1
    accumulator.successful_files = 1
    accumulator.total_source_bytes = len(text.encode("utf-8"))
    accumulator.total_extracted_chars = len(text)
    accumulator.total_signals = len(signals)
    accumulator.format_counts["synthetic_text"] += 1
    accumulator.method_counts["signal_cap_detection_only"] += 1
    accumulator.difficulty_counts["easy"] += 1
    accumulator.signal_type_counts.update(signal.get("type", "unknown") for signal in signals)
    accumulator.max_signals_in_document = len(signals)
    accumulator.signal_capEnforced = len(signals) <= MAX_SIGNALS_PER_DOCUMENT
    return accumulator.to_report()


class SuiteAccumulator:
    def __init__(self, name: str) -> None:
        self.name = name
        self.note = ""
        self.duration_seconds = 0.0
        self.processed_files = 0
        self.successful_files = 0
        self.unsupported_files = 0
        self.ocr_deferred_files = 0
        self.skipped_files = 0
        self.total_source_bytes = 0
        self.total_extracted_chars = 0
        self.total_signals = 0
        self.max_signals_in_document = 0
        self.format_counts: Counter[str] = Counter()
        self.method_counts: Counter[str] = Counter()
        self.difficulty_counts: Counter[str] = Counter()
        self.failure_difficulties: Counter[str] = Counter()
        self.signal_type_counts: Counter[str] = Counter()
        self.signal_capEnforced: bool | None = None

    def record_extracted(self, extracted: Any, *, body_size: int) -> None:
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        self.processed_files += 1
        self.successful_files += 1
        self.total_source_bytes += body_size
        self.total_extracted_chars += len(extracted.text)
        self.total_signals += len(signals)
        self.max_signals_in_document = max(self.max_signals_in_document, len(signals))
        self.format_counts[extracted.file_format] += 1
        self.method_counts[extracted.extraction_method] += 1
        self.difficulty_counts[extracted.recognition_difficulty] += 1
        self.signal_type_counts.update(signal.get("type", "unknown") for signal in signals)

    def to_report(self) -> dict[str, Any]:
        duration_ms = round(self.duration_seconds * 1000, 3)
        throughput = round(self.processed_files / self.duration_seconds, 3) if self.duration_seconds > 0 else None
        chars_per_second = round(self.total_extracted_chars / self.duration_seconds, 1) if self.duration_seconds > 0 else None
        report = {
            "name": self.name,
            "note": self.note,
            "durationMs": duration_ms,
            "throughputFilesPerSecond": throughput,
            "extractedCharsPerSecond": chars_per_second,
            "processedFiles": self.processed_files,
            "successfulFiles": self.successful_files,
            "unsupportedFiles": self.unsupported_files,
            "ocrDeferredFiles": self.ocr_deferred_files,
            "skippedFiles": self.skipped_files,
            "totalSourceBytes": self.total_source_bytes,
            "totalExtractedChars": self.total_extracted_chars,
            "totalSignals": self.total_signals,
            "maxSignalsInDocument": self.max_signals_in_document,
            "formatCounts": dict(sorted(self.format_counts.items())),
            "methodCounts": dict(sorted(self.method_counts.items())),
            "recognitionDifficulty": dict(sorted((self.difficulty_counts + self.failure_difficulties).items())),
            "signalTypeCounts": dict(sorted(self.signal_type_counts.items())),
        }
        if self.signal_capEnforced is not None:
            report["signalCapEnforced"] = self.signal_capEnforced
        return report


def aggregate_suites(suites: list[dict[str, Any]]) -> dict[str, Any]:
    duration_ms = sum(float(suite["durationMs"]) for suite in suites)
    processed_files = sum(int(suite["processedFiles"]) for suite in suites)
    successful_files = sum(int(suite["successfulFiles"]) for suite in suites)
    unsupported_files = sum(int(suite["unsupportedFiles"]) for suite in suites)
    ocr_deferred_files = sum(int(suite["ocrDeferredFiles"]) for suite in suites)
    total_source_bytes = sum(int(suite["totalSourceBytes"]) for suite in suites)
    total_extracted_chars = sum(int(suite["totalExtractedChars"]) for suite in suites)
    total_signals = sum(int(suite["totalSignals"]) for suite in suites)
    signal_types = Counter()
    formats = Counter()
    for suite in suites:
        signal_types.update(suite["signalTypeCounts"])
        formats.update(suite["formatCounts"])
    duration_seconds = duration_ms / 1000 if duration_ms > 0 else 0
    return {
        "durationMs": round(duration_ms, 3),
        "throughputFilesPerSecond": round(processed_files / duration_seconds, 3) if duration_seconds > 0 else None,
        "extractedCharsPerSecond": round(total_extracted_chars / duration_seconds, 1) if duration_seconds > 0 else None,
        "processedFiles": processed_files,
        "successfulFiles": successful_files,
        "unsupportedFiles": unsupported_files,
        "ocrDeferredFiles": ocr_deferred_files,
        "totalSourceBytes": total_source_bytes,
        "totalExtractedChars": total_extracted_chars,
        "totalSignals": total_signals,
        "formatCounts": dict(sorted(formats.items())),
        "signalTypeCounts": dict(sorted(signal_types.items())),
        "peakRssMiB": peak_rss_mib(),
        "modelCalls": 0,
        "estimatedCostUsd": 0.0,
    }


def host_report() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
    }


def safe_command(output: Path) -> str:
    try:
        display_output = output.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_output = output.name
    return f"python3 tests/core_engine_performance_benchmark.py --output {display_output}"


def peak_rss_mib() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(rss / (1024 * 1024), 3)
    return round(rss / 1024, 3)


if __name__ == "__main__":
    main()
