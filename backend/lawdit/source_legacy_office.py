"""Bounded host-local conversion for legacy binary Office source documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .source_text_locations import text_stream_location

LEGACY_OFFICE_SUFFIXES = {".doc", ".xls", ".ppt"}
LEGACY_OFFICE_CONTENT_TYPES = {
    "application/msword",
    "application/vnd.ms-office",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/x-msexcel",
    "application/x-ms-excel",
    "application/mspowerpoint",
    "application/powerpoint",
    "application/x-mspowerpoint",
}


@dataclass(frozen=True)
class LegacyOfficeExtractionResult:
    text: str
    locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


class LegacyOfficeExtractionIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def office_converter_path() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def is_legacy_office(content_type: str, suffix: str) -> bool:
    return suffix in LEGACY_OFFICE_SUFFIXES or content_type in LEGACY_OFFICE_CONTENT_TYPES


def legacy_office_format(content_type: str, suffix: str) -> str:
    if suffix == ".xls" or content_type in {"application/vnd.ms-excel", "application/x-msexcel", "application/x-ms-excel"}:
        return "xls"
    if suffix == ".ppt" or content_type in {"application/vnd.ms-powerpoint", "application/mspowerpoint", "application/powerpoint", "application/x-mspowerpoint"}:
        return "ppt"
    return "doc"


def extract_legacy_office_text(
    body: bytes,
    name: str,
    file_format: str,
    *,
    timeout_seconds: int = 25,
) -> LegacyOfficeExtractionResult:
    converter = office_converter_path()
    if not converter:
        raise LegacyOfficeExtractionIssue(f"{name} requires legacy Office conversion, but LibreOffice is not installed on this host.")

    suffix = Path(name).suffix.lower()
    if suffix not in LEGACY_OFFICE_SUFFIXES:
        suffix = f".{file_format}"

    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory)
        profile_dir = temp_root / "profile"
        output_dir = temp_root / "out"
        profile_dir.mkdir()
        output_dir.mkdir()
        input_path = temp_root / f"input{suffix}"
        input_path.write_bytes(body)
        _convert_to_text(converter, input_path, output_dir, profile_dir, name, timeout_seconds)
        text = _read_converted_text(output_dir, input_path.stem, name)

    if not text.strip():
        raise LegacyOfficeExtractionIssue(f"{name} legacy Office conversion produced no extractable text.")

    return LegacyOfficeExtractionResult(
        text,
        locations=text_stream_location(text, file_format, f"Legacy {file_format.upper()} text"),
    )


def _convert_to_text(
    converter: str,
    input_path: Path,
    output_dir: Path,
    profile_dir: Path,
    name: str,
    timeout_seconds: int,
) -> None:
    try:
        result = subprocess.run(
            [
                converter,
                "--headless",
                "--nologo",
                "--norestore",
                "--nofirststartwizard",
                f"-env:UserInstallation={profile_dir.as_uri()}",
                "--convert-to",
                "txt:Text (encoded):UTF8",
                "--outdir",
                str(output_dir),
                str(input_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise LegacyOfficeExtractionIssue(f"{name} legacy Office conversion timed out.") from error
    if result.returncode != 0:
        raise LegacyOfficeExtractionIssue(f"{name} legacy Office conversion failed.")


def _read_converted_text(output_dir: Path, stem: str, name: str) -> str:
    preferred = output_dir / f"{stem}.txt"
    if preferred.exists():
        return preferred.read_text(encoding="utf-8", errors="replace")

    outputs = sorted(output_dir.glob("*.txt"))
    if not outputs:
        raise LegacyOfficeExtractionIssue(f"{name} legacy Office conversion produced no text output.")
    return outputs[0].read_text(encoding="utf-8", errors="replace")
