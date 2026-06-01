"""Optional local OCR boundary for image source documents."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .ocr_capabilities import configured_ocr_languages, ocr_mode, tesseract_path
from .source_image_preprocessing import ocr_candidate_images
from .signal_multilingual_labels import multilingual_label_tokens


@dataclass(frozen=True)
class ImageOcrResult:
    text: str
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


class ImageOcrIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


OCR_PROFILE_ACCEPT_SCORE = 45
OCR_LABEL_TOKENS = tuple(sorted({
    "account number",
    "address",
    "bank account",
    "date of birth",
    "driver license",
    "email",
    "full name",
    "home address",
    "mobile",
    "name",
    "passport",
    "passport number",
    "phone",
    "signature",
    "street address",
    "tax id",
    "telephone",
    *multilingual_label_tokens(),
}, key=len, reverse=True))
OCR_PASSPORT_VALUE_RE = re.compile(r"\b(?=[A-Z0-9]{6,15}\b)(?=[A-Z0-9]*\d)[A-Z]{1,3}[A-Z0-9]{5,12}\b", re.IGNORECASE)
OCR_EMAIL_VALUE_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
OCR_PHONE_VALUE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,}\d{2,6}")


def extract_image_text(body: bytes, name: str, timeout_seconds: int = 12) -> str:
    return extract_image_content(body, name, timeout_seconds).text


def extract_image_content(body: bytes, name: str, timeout_seconds: int = 12) -> ImageOcrResult:
    if ocr_mode() != "local":
        raise ImageOcrIssue(f"{name} requires image OCR, but local OCR is disabled on this host.")

    tesseract = tesseract_path()
    if not tesseract:
        raise ImageOcrIssue(f"{name} requires image OCR, but Tesseract is not installed on this host.")

    suffix = Path(name).suffix.lower() or ".png"
    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / f"source{suffix}"
        image_path.write_bytes(body)
        ocr_results = []
        failed = False
        timed_out = False
        for candidate in ocr_candidate_images(image_path, Path(directory)):
            profile_results = []
            for language_profile in _ocr_language_profiles():
                try:
                    result = subprocess.run(
                        _tesseract_command(tesseract, str(candidate), language_profile),
                        capture_output=True,
                        check=False,
                        text=True,
                        timeout=timeout_seconds,
                    )
                except subprocess.TimeoutExpired:
                    failed = True
                    timed_out = True
                    continue
                failed = failed or result.returncode != 0
                if result.returncode == 0:
                    text, regions = _parse_tesseract_tsv(result.stdout)
                    if text:
                        profile_results.append((text, regions))
                        if _ocr_result_score(text, regions) >= OCR_PROFILE_ACCEPT_SCORE:
                            break
            best_profile = _best_ocr_profile_result(profile_results)
            if best_profile:
                ocr_results.append(best_profile)

    if not ocr_results and timed_out:
        raise ImageOcrIssue(f"{name} image OCR timed out.")
    if not ocr_results and failed:
        raise ImageOcrIssue(f"{name} image OCR failed.")

    text, regions = _join_ocr_results(ocr_results)
    if not text:
        raise ImageOcrIssue(f"{name} has no extractable OCR text.")

    return ImageOcrResult(text, text_locations=_image_text_locations(text, regions))


def _tesseract_command_for_profile(tesseract: str, image_path: str, languages: str) -> list[str]:
    command = [tesseract, image_path, "stdout", "--psm", "6"]
    if languages:
        command.extend(["-l", languages])
    command.append("tsv")
    return command


def _tesseract_command(tesseract: str, image_path: str, languages: str | None = None) -> list[str]:
    return _tesseract_command_for_profile(tesseract, image_path, languages or "")


def _ocr_language_profiles() -> tuple[str | None, ...]:
    languages = _unique_languages(configured_ocr_languages())
    if not languages:
        return (None,)

    profiles: list[str] = []

    def add_profile(candidates: tuple[str, ...]) -> None:
        selected = tuple(language for language in candidates if language in languages)
        if not selected:
            return
        profile = "+".join(selected)
        if profile not in profiles:
            profiles.append(profile)

    add_profile(("chi_sim", "eng"))
    add_profile(("jpn", "eng"))
    add_profile(("kor", "eng"))
    add_profile(("ara", "eng"))

    if len(languages) <= 5:
        add_profile(languages)
        return tuple(profiles)

    add_profile(("eng", "chi_sim", "deu", "fra", "spa"))
    add_profile(("eng", "por", "ita", "nld", "pol"))
    add_profile(("eng", "jpn", "kor", "ara"))

    covered = {language for profile in profiles for language in profile.split("+")}
    remaining = tuple(language for language in languages if language not in covered)
    for index in range(0, len(remaining), 5):
        profiles.append("+".join(remaining[index:index + 5]))

    return tuple(profiles[:6])


def _unique_languages(languages: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    unique = []
    for language in languages:
        if language not in seen:
            unique.append(language)
            seen.add(language)
    return tuple(unique)


def _join_ocr_results(results: list[tuple[str, tuple[dict[str, Any], ...]]]) -> tuple[str, tuple[dict[str, Any], ...]]:
    fragments: list[str] = []
    regions: list[dict[str, Any]] = []
    offset = 0
    seen_text: set[str] = set()
    for text, text_regions in results:
        normalized = " ".join(text.split())
        if not normalized or normalized in seen_text:
            continue
        seen_text.add(normalized)
        if fragments:
            fragments.append("\n")
            offset += 1
        fragments.append(text)
        regions.extend(_shift_regions(text_regions, offset))
        offset += len(text)
    return "".join(fragments), tuple(regions)


def _best_ocr_profile_result(results: list[tuple[str, tuple[dict[str, Any], ...]]]) -> tuple[str, tuple[dict[str, Any], ...]] | None:
    if not results:
        return None
    return max(results, key=lambda result: _ocr_result_score(result[0], result[1]))


def _ocr_result_score(text: str, regions: tuple[dict[str, Any], ...]) -> float:
    normalized = _normalize_ocr_text(text)
    alnum_count = sum(1 for character in normalized if character.isalnum())
    score = min(alnum_count / 8, 30)
    score += _average_ocr_confidence(regions) / 5
    score += _label_score(normalized)
    score += 25 if OCR_EMAIL_VALUE_RE.search(text) else 0
    score += 30 if OCR_PASSPORT_VALUE_RE.search(text) else 0
    score += 15 if OCR_PHONE_VALUE_RE.search(text) else 0
    score -= _tsv_dump_penalty(text)
    return score


def _normalize_ocr_text(text: str) -> str:
    return " ".join(text.casefold().replace("_", " ").replace("-", " ").split())


def _average_ocr_confidence(regions: tuple[dict[str, Any], ...]) -> float:
    values = [
        float(region["ocrConfidence"])
        for region in regions
        if isinstance(region.get("ocrConfidence"), (int, float)) and float(region["ocrConfidence"]) >= 0
    ]
    if not values:
        return 0
    return sum(values) / len(values)


def _label_score(normalized_text: str) -> int:
    return min(sum(1 for token in OCR_LABEL_TOKENS if _normalize_ocr_text(token) in normalized_text) * 20, 80)


def _tsv_dump_penalty(text: str) -> int:
    tsv_like_lines = sum(1 for line in text.splitlines() if re.match(r"^\s*\d+\t\d+\t\d+\t\d+\t\d+", line))
    return min(tsv_like_lines * 15, 90)


def _shift_regions(regions: tuple[dict[str, Any], ...], offset: int) -> tuple[dict[str, Any], ...]:
    shifted = []
    for region in regions:
        item = dict(region)
        if isinstance(item.get("start"), int):
            item["start"] += offset
        if isinstance(item.get("end"), int):
            item["end"] += offset
        shifted.append(item)
    return tuple(shifted)


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
