"""Optional local OCR boundary for image source documents."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class ImageOcrIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def extract_image_text(body: bytes, name: str, timeout_seconds: int = 12) -> str:
    if os.environ.get("DATASENTINEL_OCR_MODE", "local").strip().lower() != "local":
        raise ImageOcrIssue(f"{name} requires image OCR, but local OCR is disabled on this host.")

    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise ImageOcrIssue(f"{name} requires image OCR, but Tesseract is not installed on this host.")

    suffix = Path(name).suffix.lower() or ".png"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix) as image_file:
            image_file.write(body)
            image_file.flush()
            result = subprocess.run(
                [tesseract, image_file.name, "stdout", "--psm", "6"],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
    except subprocess.TimeoutExpired as error:
        raise ImageOcrIssue(f"{name} image OCR timed out.") from error

    if result.returncode != 0:
        raise ImageOcrIssue(f"{name} image OCR failed.")

    text = result.stdout.strip()
    if not text:
        raise ImageOcrIssue(f"{name} has no extractable OCR text.")

    return text
