"""Prelaunch byte budgets by source document family."""

from __future__ import annotations

from pathlib import Path

from .source_media_recognition import is_image, is_video_media

MAX_TEXT_DOCUMENT_BYTES = 1_000_000
MAX_COMPLEX_DOCUMENT_BYTES = 8_000_000
MAX_VIDEO_BYTES = 8_000_000
MAX_SOURCE_FILES = 500

# Backward-compatible name used by reports for the text-stream budget.
MAX_DOCUMENT_BYTES = MAX_TEXT_DOCUMENT_BYTES

COMPLEX_DOCUMENT_SUFFIXES = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".doc",
    ".xls",
    ".ppt",
    ".odt",
    ".ods",
    ".odp",
    ".eml",
    ".rtf",
    ".zip",
}
COMPLEX_CONTENT_TYPES = {
    "application/pdf",
    "application/rtf",
    "message/rfc822",
    "application/eml",
    "application/zip",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def max_bytes_for_file(content_type: str, name: str) -> int:
    suffix = Path(name).suffix.lower()
    normalized_type = content_type.lower().split(";", 1)[0].strip()
    if is_video_media(normalized_type, suffix):
        return MAX_VIDEO_BYTES
    if is_image(normalized_type, suffix) or suffix in COMPLEX_DOCUMENT_SUFFIXES or normalized_type in COMPLEX_CONTENT_TYPES:
        return MAX_COMPLEX_DOCUMENT_BYTES
    return MAX_TEXT_DOCUMENT_BYTES


def extraction_limit_warning(name: str, content_type: str) -> str:
    limit = max_bytes_for_file(content_type, name)
    if limit == MAX_COMPLEX_DOCUMENT_BYTES:
        return f"{name} exceeds the prelaunch 8 MB bounded document extraction limit."
    return f"{name} exceeds the prelaunch 1 MB text extraction limit."
