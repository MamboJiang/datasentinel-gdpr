"""PDF text-layer extraction with optional local OCR fallback."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from .ocr_capabilities import ocr_mode, pdftoppm_path
from .source_image_ocr import ImageOcrIssue, extract_image_content

try:
    from pypdf import mult as _pdf_matrix_mult
except Exception:  # pragma: no cover - optional when tests inject a reader
    _pdf_matrix_mult = None

MAX_PDF_OCR_PAGES = 5
PDF_OCR_DPI = 300


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    file_format: str
    extraction_method: str
    recognition_difficulty: str
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)
    warnings: tuple[str, ...] = field(default=(), kw_only=True)
    ocr_deferred: bool = field(default=False, kw_only=True)


class PdfExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported", ocr_deferred: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty
        self.ocr_deferred = ocr_deferred


def extract_pdf_content(body: bytes, name: str, pdf_reader_cls: Any) -> PdfExtractionResult:
    text_layer_blocker: str | None = None
    if pdf_reader_cls is not None:
        try:
            reader = pdf_reader_cls(BytesIO(body), strict=False)
            page_records = _text_layer_page_records(reader)
            text_result = _text_layer_result(page_records)
        except Exception:
            text_layer_blocker = f"{name} PDF text extraction failed."
        else:
            if text_result.text.strip():
                return _with_targeted_page_ocr(body, name, page_records, text_result)
            text_layer_blocker = f"{name} has no extractable PDF text layer."
    else:
        text_layer_blocker = f"{name} is a PDF, but PDF text extraction is not installed on this host."

    try:
        return _ocr_result(body, name)
    except PdfExtractionIssue as error:
        detail = f"{text_layer_blocker} {error.detail}"
        raise PdfExtractionIssue(detail, recognition_difficulty="hard", ocr_deferred=True) from error


def extract_pdf_ocr_text(body: bytes, name: str, timeout_seconds: int = 30) -> str:
    return _ocr_result(body, name, timeout_seconds).text


def _text_layer_page_records(reader: Any) -> tuple[dict[str, Any], ...]:
    return tuple(_page_text_record(page) for page in reader.pages)


def _text_layer_result(page_records: tuple[dict[str, Any], ...]) -> PdfExtractionResult:
    text, locations = _join_page_records(page_records, "pdf_text_layer")
    return PdfExtractionResult(text, "pdf_text_layer", "pdf_text_layer", "moderate", text_locations=locations)


def _with_targeted_page_ocr(
    body: bytes,
    name: str,
    page_records: tuple[dict[str, Any], ...],
    text_result: PdfExtractionResult,
) -> PdfExtractionResult:
    target_pages = [
        page_number
        for page_number, page_record in enumerate(page_records, start=1)
        if not str(page_record.get("text") or "").strip() or bool(page_record.get("hasImages"))
    ]
    if not target_pages:
        return text_result
    try:
        ocr_records = _ocr_selected_page_records(body, name, target_pages[:MAX_PDF_OCR_PAGES])
    except PdfExtractionIssue as error:
        return _mixed_ocr_deferred_result(text_result, name, error.detail)
    if not ocr_records:
        return text_result

    combined = list(page_records)
    for page_number, page_record in ocr_records.items():
        if 1 <= page_number <= len(combined):
            existing = combined[page_number - 1]
            combined[page_number - 1] = _merge_page_ocr_record(existing, page_record)
    text, locations = _join_page_records(tuple(combined), "pdf_text_layer")
    return PdfExtractionResult(text, "pdf_mixed", "pdf_text_layer_with_page_ocr", "hard", text_locations=locations)


def _mixed_ocr_deferred_result(text_result: PdfExtractionResult, name: str, detail: str) -> PdfExtractionResult:
    return PdfExtractionResult(
        text_result.text,
        text_result.file_format,
        text_result.extraction_method,
        "hard",
        text_locations=text_result.text_locations,
        warnings=(f"{name} mixed PDF page OCR deferred: {detail}",),
        ocr_deferred=True,
    )


def _merge_page_ocr_record(text_record: dict[str, Any], ocr_record: dict[str, Any]) -> dict[str, Any]:
    text = str(text_record.get("text") or "")
    ocr_text = str(ocr_record.get("text") or "")
    if not text.strip():
        return ocr_record
    if not ocr_text.strip():
        return text_record
    separator = "\n"
    shift = len(text) + len(separator)
    regions = list(text_record.get("regions") or ())
    regions.extend(_shift_regions(tuple(ocr_record.get("regions") or ()), shift))
    return {
        **text_record,
        "text": f"{text}{separator}{ocr_text}",
        "regions": tuple(regions),
        "format": "pdf_ocr",
    }


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


def _ocr_result(body: bytes, name: str, timeout_seconds: int = 30) -> PdfExtractionResult:
    if ocr_mode() != "local":
        raise PdfExtractionIssue(f"{name} requires PDF OCR, but local OCR is disabled on this host.", ocr_deferred=True)

    pdftoppm = pdftoppm_path()
    if not pdftoppm:
        raise PdfExtractionIssue(f"{name} requires PDF OCR, but pdftoppm is not installed on this host.", ocr_deferred=True)

    with tempfile.TemporaryDirectory() as directory:
        temp_dir = Path(directory)
        pdf_path = temp_dir / "source.pdf"
        image_prefix = temp_dir / "page"
        pdf_path.write_bytes(body)
        try:
            result = subprocess.run(
                [
                    pdftoppm,
                    "-png",
                    "-r",
                    str(PDF_OCR_DPI),
                    "-f",
                    "1",
                    "-l",
                    str(MAX_PDF_OCR_PAGES),
                    str(pdf_path),
                    str(image_prefix),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise PdfExtractionIssue(f"{name} PDF rasterization timed out.", ocr_deferred=True) from error

        if result.returncode != 0:
            raise PdfExtractionIssue(f"{name} PDF rasterization failed.", ocr_deferred=True)

        page_records: list[dict[str, Any]] = []
        for image_path in sorted(temp_dir.glob("page-*.png")):
            try:
                image_result = extract_image_content(image_path.read_bytes(), image_path.name)
            except ImageOcrIssue as error:
                raise PdfExtractionIssue(error.detail, ocr_deferred=True) from error
            page_records.append({"text": image_result.text, "regions": _image_ocr_regions(image_result.text_locations)})

    text, locations = _join_page_records(tuple(page_records), "pdf_ocr")
    if not text.strip():
        raise PdfExtractionIssue(f"{name} PDF OCR produced no text.", ocr_deferred=True)
    return PdfExtractionResult(text, "pdf_ocr", "pdf_page_image_ocr", "hard", text_locations=locations)


def _ocr_selected_page_records(body: bytes, name: str, page_numbers: list[int], timeout_seconds: int = 30) -> dict[int, dict[str, Any]]:
    if ocr_mode() != "local":
        raise PdfExtractionIssue(f"{name} requires PDF OCR, but local OCR is disabled on this host.", ocr_deferred=True)

    pdftoppm = pdftoppm_path()
    if not pdftoppm:
        raise PdfExtractionIssue(f"{name} requires PDF OCR, but pdftoppm is not installed on this host.", ocr_deferred=True)

    page_records: dict[int, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory() as directory:
        temp_dir = Path(directory)
        pdf_path = temp_dir / "source.pdf"
        pdf_path.write_bytes(body)
        for page_number in page_numbers:
            page_dir = temp_dir / f"page-{page_number}"
            page_dir.mkdir()
            image_prefix = page_dir / "page"
            try:
                result = subprocess.run(
                    [
                        pdftoppm,
                        "-png",
                        "-r",
                        str(PDF_OCR_DPI),
                        "-f",
                        str(page_number),
                        "-l",
                        str(page_number),
                        str(pdf_path),
                        str(image_prefix),
                    ],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                raise PdfExtractionIssue(f"{name} PDF rasterization timed out.", ocr_deferred=True) from error
            if result.returncode != 0:
                raise PdfExtractionIssue(f"{name} PDF rasterization failed.", ocr_deferred=True)
            image_paths = sorted(page_dir.glob("page-*.png"))
            if not image_paths:
                continue
            try:
                image_result = extract_image_content(image_paths[0].read_bytes(), image_paths[0].name)
            except ImageOcrIssue as error:
                raise PdfExtractionIssue(error.detail, ocr_deferred=True) from error
            if image_result.text.strip():
                page_records[page_number] = {
                    "text": image_result.text,
                    "regions": _image_ocr_regions(image_result.text_locations),
                    "format": "pdf_ocr",
                }
    return page_records


def _image_ocr_regions(text_locations: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    if not text_locations:
        return ()
    regions = text_locations[0].get("regions")
    return tuple(regions) if isinstance(regions, (list, tuple)) else ()


def _page_text_record(page: Any) -> dict[str, Any]:
    parts: list[str] = []
    regions: list[dict[str, Any]] = []
    page_width, page_height = _page_size(page)
    has_images = _page_has_images(page)

    def visitor(text: str, user_matrix: Any, text_matrix: Any, font_dictionary: Any, font_size: float) -> None:
        if not text:
            return
        start = sum(len(part) for part in parts)
        parts.append(text)
        region = _text_region(text, user_matrix, text_matrix, font_size, page_width, page_height)
        if region:
            region["start"] = start
            region["end"] = start + len(text)
            regions.append(region)

    try:
        extracted = page.extract_text(visitor_text=visitor)
    except Exception:
        return {"text": page.extract_text() or "", "regions": (), "pageWidth": page_width, "pageHeight": page_height, "format": "pdf_text_layer", "hasImages": has_images}

    text = "".join(parts) if parts else (extracted or "")
    return {"text": text, "regions": tuple(regions), "pageWidth": page_width, "pageHeight": page_height, "format": "pdf_text_layer", "hasImages": has_images}


def _page_has_images(page: Any) -> bool:
    try:
        resources = page.get("/Resources") or {}
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        xobjects = resources.get("/XObject") if hasattr(resources, "get") else None
        if hasattr(xobjects, "get_object"):
            xobjects = xobjects.get_object()
        for value in (xobjects or {}).values():
            resolved = value.get_object() if hasattr(value, "get_object") else value
            if hasattr(resolved, "get") and str(resolved.get("/Subtype")) == "/Image":
                return True
    except Exception:
        return False
    return False


def _text_region(
    text: str,
    user_matrix: Any,
    text_matrix: Any,
    font_size: float,
    page_width: float | None,
    page_height: float | None,
) -> dict[str, Any] | None:
    origin = _text_origin(user_matrix, text_matrix)
    if not origin:
        return None

    x, y = origin
    height = _positive_float(font_size) or 1.0
    width = max(height * 0.5 * len(text.strip() or text), 1.0)
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(width, 2),
        "height": round(height, 2),
        "pageWidth": round(page_width, 2) if page_width else None,
        "pageHeight": round(page_height, 2) if page_height else None,
        "unit": "pt",
        "origin": "bottom_left",
        "confidence": "estimated",
    }


def _text_origin(user_matrix: Any, text_matrix: Any) -> tuple[float, float] | None:
    try:
        if _pdf_matrix_mult:
            combined = _pdf_matrix_mult(text_matrix, user_matrix)
            return float(combined[4]), float(combined[5])
        return float(user_matrix[4]), float(user_matrix[5])
    except Exception:
        return None


def _page_size(page: Any) -> tuple[float | None, float | None]:
    media_box = getattr(page, "mediabox", None)
    try:
        return float(media_box.width), float(media_box.height)
    except Exception:
        return None, None


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if parsed > 0 else None


def _join_page_records(page_records: tuple[dict[str, Any], ...], file_format: str) -> tuple[str, tuple[dict[str, Any], ...]]:
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    offset = 0
    for page_index, page_record in enumerate(page_records, start=1):
        page_text = str(page_record.get("text") or "")
        if page_index > 1:
            fragments.append("\n")
            offset += 1
        start = offset
        fragments.append(page_text)
        offset += len(page_text)
        end = offset
        if page_text.strip():
            page_format = str(page_record.get("format") or file_format)
            location = {
                "format": page_format,
                "label": f"Page {page_index}",
                "start": start,
                "end": end,
                "page": page_index,
            }
            regions = page_record.get("regions")
            if regions:
                location["regions"] = tuple(regions)
            locations.append(location)
    return "".join(fragments), tuple(locations)
