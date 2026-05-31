"""Bounded ZIP archive extraction with public-safe member anchors."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from zipfile import BadZipFile, LargeZipFile, ZipFile

SUPPORTED_ARCHIVE_SUFFIXES = {".zip"}
ARCHIVE_CONTENT_TYPES = {"application/zip", "application/x-zip-compressed"}
MAX_ARCHIVE_MEMBERS = 32
MAX_ARCHIVE_MEMBER_BYTES = 1_000_000
MAX_ARCHIVE_TOTAL_BYTES = 2_000_000
MAX_EXTRACTED_TEXT_CHARS = 300_000


@dataclass(frozen=True)
class ArchiveTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class ArchiveExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_zip_archive_text(
    body: bytes,
    name: str,
    extract_member: Callable[[bytes, str], Any],
) -> ArchiveTextExtraction:
    try:
        with ZipFile(BytesIO(body)) as archive:
            members = _candidate_members(archive, name)
            return _extract_members(archive, members, extract_member, name)
    except (BadZipFile, LargeZipFile) as error:
        raise ArchiveExtractionIssue(f"{name} is not a readable ZIP archive.") from error


def is_archive_like(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_ARCHIVE_SUFFIXES or content_type in ARCHIVE_CONTENT_TYPES


def _candidate_members(archive: ZipFile, name: str) -> list[Any]:
    members = [
        info for info in archive.infolist()
        if not info.is_dir() and not _is_nested_archive(info.filename) and not _is_metadata_member(info.filename)
    ]
    if not members:
        raise ArchiveExtractionIssue(f"{name} has no supported ZIP members.", recognition_difficulty="hard")
    total_size = sum(max(info.file_size, 0) for info in members[:MAX_ARCHIVE_MEMBERS])
    if total_size > MAX_ARCHIVE_TOTAL_BYTES:
        raise ArchiveExtractionIssue(f"{name} exceeds the prelaunch ZIP extraction limit.")
    return members[:MAX_ARCHIVE_MEMBERS]


def _extract_members(
    archive: ZipFile,
    members: list[Any],
    extract_member: Callable[[bytes, str], Any],
    name: str,
) -> ArchiveTextExtraction:
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    for member_index, info in enumerate(members, start=1):
        try:
            child = extract_member(_read_member(archive, info, name), _safe_member_name(info.filename))
        except Exception:
            continue
        if not str(child.text).strip():
            continue
        archive_start = _append_fragment(fragments, str(child.text))
        _append_locations(locations, getattr(child, "text_locations", ()), archive_start, member_index, len(str(child.text)))
    text = "\n".join(fragments)
    if not text.strip():
        raise ArchiveExtractionIssue(f"{name} has no extractable ZIP member text.", recognition_difficulty="hard")
    return ArchiveTextExtraction(text[:MAX_EXTRACTED_TEXT_CHARS], tuple(locations))


def _read_member(archive: ZipFile, info: Any, name: str) -> bytes:
    if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ArchiveExtractionIssue(f"{name} has a ZIP member over the prelaunch extraction limit.")
    with archive.open(info) as stream:
        data = stream.read(MAX_ARCHIVE_MEMBER_BYTES + 1)
    if len(data) > MAX_ARCHIVE_MEMBER_BYTES:
        raise ArchiveExtractionIssue(f"{name} has a ZIP member over the prelaunch extraction limit.")
    return data


def _append_locations(
    locations: list[dict[str, Any]],
    child_locations: tuple[dict[str, Any], ...],
    archive_start: int,
    member_index: int,
    child_length: int,
) -> None:
    for child_location in child_locations or (_whole_member_location(child_length),):
        child_start = int(child_location.get("start", 0))
        child_end = int(child_location.get("end", child_start))
        selector = _member_selector(member_index, child_location)
        locations.append({
            "format": "zip",
            "label": selector["blockLabel"],
            "start": archive_start + child_start,
            "end": archive_start + child_end,
            "selector": selector,
        })


def _member_selector(member_index: int, child_location: dict[str, Any]) -> dict[str, Any]:
    child_selector = child_location.get("selector")
    selector = dict(child_selector) if isinstance(child_selector, dict) else {"type": "structurePath"}
    selector["containerType"] = "zip"
    selector["memberIndex"] = member_index
    selector["memberPath"] = f"/member[{member_index}]"
    selector["childFormat"] = str(child_location.get("format") or "unknown")
    child_label = str(child_location.get("label") or "").strip()
    selector["blockLabel"] = f"ZIP member {member_index}" + (f": {child_label}" if child_label else "")
    if selector.get("type") == "structurePath":
        child_path = str(selector.get("path") or "")
        selector["path"] = selector["memberPath"] + (child_path if child_path.startswith("/") else f"/{child_path}" if child_path else "")
    return selector


def _whole_member_location(child_length: int) -> dict[str, Any]:
    return {
        "format": "unknown",
        "label": "ZIP member",
        "start": 0,
        "end": child_length,
        "selector": {"type": "structurePath"},
    }


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _safe_member_name(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"member{suffix}" if suffix else "member"


def _is_nested_archive(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_ARCHIVE_SUFFIXES


def _is_metadata_member(filename: str) -> bool:
    return filename.startswith("__MACOSX/") or Path(filename).name.startswith(".")
