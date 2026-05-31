"""Optional local OCR boundary for image source documents."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .ocr_capabilities import configured_ocr_languages, ocr_mode, tesseract_path


@dataclass(frozen=True)
class ImageOcrResult:
    text: str
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


class ImageOcrIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def extract_image_text(body: bytes, name: str, timeout_seconds: int = 12) -> str:
    return extract_image_content(body, name, timeout_seconds).text


def extract_image_content(body: bytes, name: str, timeout_seconds: int = 12) -> ImageOcrResult:
    if ocr_mode() != "local":
        raise ImageOcrIssue(f"{name} requires image OCR, but local OCR is disabled on this host.")

    tesseract = tesseract_path()
    if not tesseract:
        raise ImageOcrIssue(f"{name} requires image OCR, but Tesseract is not installed on this host.")

    suffix = Path(name).suffix.lower() or ".png"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix) as image_file:
            image_file.write(body)
            image_file.flush()
            result = subprocess.run(
                _tesseract_command(tesseract, image_file.name),
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
    except subprocess.TimeoutExpired as error:
        raise ImageOcrIssue(f"{name} image OCR timed out.") from error

    if result.returncode != 0:
        raise ImageOcrIssue(f"{name} image OCR failed.")

    text, regions = _parse_tesseract_tsv(result.stdout)
    if not text:
        raise ImageOcrIssue(f"{name} has no extractable OCR text.")

    return ImageOcrResult(text, text_locations=_image_text_locations(text, regions))


def _tesseract_command(tesseract: str, image_path: str) -> list[str]:
    command = [tesseract, image_path, "stdout", "--psm", "6"]
    languages = "+".join(configured_ocr_languages())
    if languages:
        command.extend(["-l", languages])
    command.append("tsv")
    return command


def _parse_tesseract_tsv(tsv_output: str) -> tuple[str, tuple[dict[str, Any], ...]]:
    reader = csv.DictReader(StringIO(tsv_output), delimiter="\t")
    page_sizes: dict[int, tuple[float, float]] = {}
    words: list[dict[str, Any]] = []
    for row in reader:
        level = _int_value(row.get("level"))
        page_num = _int_value(row.get("page_num")) or 1
        if level == 1:
            page_width = _float_value(row.get("width"))
            page_height = _float_value(row.get("height"))
            if page_width and page_height:
                page_sizes[page_num] = (page_width, page_height)
        if level != 5:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        word = {
            "text": text,
            "lineKey": (
                page_num,
                _int_value(row.get("block_num")) or 0,
                _int_value(row.get("par_num")) or 0,
                _int_value(row.get("line_num")) or 0,
            ),
            "x": _float_value(row.get("left")),
            "y": _float_value(row.get("top")),
            "width": _float_value(row.get("width")),
            "height": _float_value(row.get("height")),
            "pageSize": page_sizes.get(page_num),
            "ocrConfidence": _float_value(row.get("conf")),
        }
        words.append(word)
    return _join_ocr_words(words)


def _join_ocr_words(words: list[dict[str, Any]]) -> tuple[str, tuple[dict[str, Any], ...]]:
    fragments: list[str] = []
    regions: list[dict[str, Any]] = []
    previous_line: tuple[int, int, int, int] | None = None
    previous_text: str | None = None
    offset = 0
    for word in words:
        line_key = word["lineKey"]
        text = str(word["text"])
        if previous_line is None:
            previous_line = line_key
        elif line_key != previous_line:
            fragments.append("\n")
            offset += 1
            previous_line = line_key
            previous_text = None
        else:
            separator = _ocr_word_separator(previous_text, text)
            fragments.append(separator)
            offset += len(separator)

        start = offset
        fragments.append(text)
        offset += len(text)
        previous_text = text
        region = _ocr_region(word, start, offset)
        if region:
            regions.append(region)
    return "".join(fragments), tuple(regions)


def _ocr_word_separator(previous_text: str | None, current_text: str) -> str:
    if not previous_text:
        return ""
    if _is_joining_punctuation(previous_text) or _is_joining_punctuation(current_text):
        return ""
    if _touches_cjk_kana_hangul(previous_text) or _touches_cjk_kana_hangul(current_text):
        return ""
    return " "


def _is_joining_punctuation(value: str) -> bool:
    return value in {":", "：", ".", "．", "。", ",", "，", ";", "；", "(", ")", "[", "]", "{", "}", "/", "\\"}


def _touches_cjk_kana_hangul(value: str) -> bool:
    if not value:
        return False
    return _is_cjk_kana_hangul(value[0]) or _is_cjk_kana_hangul(value[-1])


def _is_cjk_kana_hangul(character: str) -> bool:
    return (
        "\u4e00" <= character <= "\u9fff"
        or "\u3040" <= character <= "\u30ff"
        or "\uac00" <= character <= "\ud7af"
    )


def _ocr_region(word: dict[str, Any], start: int, end: int) -> dict[str, Any] | None:
    if not all(isinstance(word.get(key), (int, float)) for key in ("x", "y", "width", "height")):
        return None
    region: dict[str, Any] = {
        "start": start,
        "end": end,
        "x": round(float(word["x"]), 2),
        "y": round(float(word["y"]), 2),
        "width": round(float(word["width"]), 2),
        "height": round(float(word["height"]), 2),
        "unit": "px",
        "origin": "top_left",
        "confidence": "ocr",
    }
    page_size = word.get("pageSize")
    if isinstance(page_size, tuple) and len(page_size) == 2:
        region["pageWidth"] = round(float(page_size[0]), 2)
        region["pageHeight"] = round(float(page_size[1]), 2)
    if isinstance(word.get("ocrConfidence"), (int, float)):
        region["ocrConfidence"] = round(float(word["ocrConfidence"]), 2)
    return region


def _image_text_locations(text: str, regions: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    location: dict[str, Any] = {
        "format": "image_ocr",
        "label": "Image OCR text",
        "start": 0,
        "end": len(text),
    }
    if regions:
        location["regions"] = regions
    return (location,)


def _int_value(value: str | None) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _float_value(value: str | None) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
