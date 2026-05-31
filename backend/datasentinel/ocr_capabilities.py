"""Host-local OCR capability probes for prelaunch extraction."""

from __future__ import annotations

import os
import shutil
from typing import Any


def ocr_mode() -> str:
    return os.environ.get("DATASENTINEL_OCR_MODE", "local").strip().lower() or "local"


def configured_ocr_languages() -> tuple[str, ...]:
    value = os.environ.get("DATASENTINEL_OCR_LANGS", "").strip()
    if not value:
        return ()
    return tuple(part.strip() for part in value.replace(",", "+").split("+") if part.strip())


def tesseract_path() -> str | None:
    return shutil.which("tesseract")


def pdftoppm_path() -> str | None:
    return shutil.which("pdftoppm")


def ocr_capabilities() -> dict[str, Any]:
    mode = ocr_mode()
    tesseract = tesseract_path()
    pdftoppm = pdftoppm_path()
    local_enabled = mode == "local"
    return {
        "ocrMode": mode,
        "languagesConfigured": list(configured_ocr_languages()),
        "tesseractAvailable": bool(tesseract),
        "pdftoppmAvailable": bool(pdftoppm),
        "imageOcrAvailable": local_enabled and bool(tesseract),
        "pdfOcrAvailable": local_enabled and bool(tesseract and pdftoppm),
    }
