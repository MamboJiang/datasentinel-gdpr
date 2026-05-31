"""Aggregate extraction batch metadata for public scan summaries."""

from __future__ import annotations

from typing import Any

DIFFICULTY_LEVELS = ("easy", "moderate", "hard", "unsupported")


def method_counts(documents: list[Any], unsupported_files: int, ocr_deferred_files: int) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for document in documents:
        counts[document.extraction_method] = counts.get(document.extraction_method, 0) + 1
    if ocr_deferred_files:
        counts["ocr_deferred"] = ocr_deferred_files
    skipped = unsupported_files - ocr_deferred_files
    if skipped > 0:
        counts["unsupported"] = skipped
    return [
        {"method": method, "files": files, "status": "warning" if method in {"ocr_deferred", "unsupported"} else "completed"}
        for method, files in sorted(counts.items())
    ]


def format_counts(documents: list[Any], failure_difficulties: list[str]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = {}
    for document in documents:
        key = (document.file_format, document.recognition_difficulty, document.extraction_method)
        counts[key] = counts.get(key, 0) + 1
    for difficulty in failure_difficulties:
        key = ("ocr_deferred", "hard", "ocr_deferred") if difficulty == "ocr_deferred" else ("unsupported", difficulty, "unsupported")
        counts[key] = counts.get(key, 0) + 1
    return [
        {"format": file_format, "difficulty": difficulty, "method": method, "files": files}
        for (file_format, difficulty, method), files in sorted(counts.items())
    ]


def difficulty_counts(documents: list[Any], failure_difficulties: list[str]) -> dict[str, int]:
    counts = {level: 0 for level in DIFFICULTY_LEVELS}
    for document in documents:
        counts[document.recognition_difficulty] = counts.get(document.recognition_difficulty, 0) + 1
    for difficulty in failure_difficulties:
        key = "hard" if difficulty == "ocr_deferred" else difficulty
        counts[key] = counts.get(key, 0) + 1
    return counts
