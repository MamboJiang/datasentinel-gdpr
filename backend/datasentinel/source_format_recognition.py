"""Bounded local format recognition for prelaunch source scans."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile

from .source_image_ocr import ImageOcrIssue, extract_image_text
from .source_media_recognition import (
    MEDIA_ACCEPT_HEADER,
    SUPPORTED_MEDIA_SUFFIXES,
    clean_video_transcript,
    is_image,
    is_video_media,
    is_video_transcript,
)

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - exercised when optional runtime dependency is absent
    PdfReader = None  # type: ignore[assignment]

SUPPORTED_TEXT_SUFFIXES = {".txt", ".csv", ".tsv", ".json", ".md", ".log", ".xml", ".html"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx"}
SUPPORTED_SUFFIXES = (
    SUPPORTED_TEXT_SUFFIXES
    | SUPPORTED_PDF_SUFFIXES
    | SUPPORTED_OFFICE_SUFFIXES
    | SUPPORTED_MEDIA_SUFFIXES
)
TEXT_CONTENT_TYPES = {"text/", "application/json", "application/xml", "application/x-ndjson"}
PDF_CONTENT_TYPES = {"application/pdf"}
OFFICE_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DOWNLOAD_ACCEPT_HEADER = (
    "text/*, application/json, application/xml;q=0.9, application/pdf;q=0.8, "
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document;q=0.8, "
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;q=0.8, "
    f"application/vnd.openxmlformats-officedocument.presentationml.presentation;q=0.8, {MEDIA_ACCEPT_HEADER}, */*;q=0.1"
)
DIFFICULTY_LEVELS = ("easy", "moderate", "hard", "unsupported")
MAX_OOXML_XML_BYTES = 4_000_000
MAX_OOXML_MEMBER_BYTES = 2_000_000
MAX_EXTRACTED_TEXT_CHARS = 300_000
_DEFAULT_PDF_READER = object()


@dataclass(frozen=True)
class SourceDocument:
    name: str
    source_path: str
    text: str
    size_bytes: int
    family: str
    file_format: str = "text"
    extraction_method: str = "utf8_text"
    recognition_difficulty: str = "easy"


@dataclass(frozen=True)
class SourceDocumentBatch:
    documents: list[SourceDocument]
    total_files: int
    total_bytes: int
    unsupported_files: int
    warnings: list[str]
    family: str
    extraction_method: str
    method_counts: list[dict[str, Any]] | None = None
    format_counts: list[dict[str, Any]] | None = None
    recognition_difficulty: dict[str, int] | None = None
    ocr_deferred_files: int = 0


@dataclass(frozen=True)
class ExtractedDocumentContent:
    text: str
    file_format: str
    extraction_method: str
    recognition_difficulty: str


class DocumentExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported", ocr_deferred: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty
        self.ocr_deferred = ocr_deferred


def build_document_batch(
    *,
    documents: list[SourceDocument],
    total_files: int,
    total_bytes: int,
    unsupported_files: int,
    warnings: list[str],
    family: str,
    extraction_method: str,
    ocr_deferred_files: int = 0,
    failure_difficulties: list[str] | None = None,
) -> SourceDocumentBatch:
    failures = failure_difficulties or ["unsupported"] * unsupported_files
    return SourceDocumentBatch(
        documents=documents,
        total_files=total_files,
        total_bytes=total_bytes,
        unsupported_files=unsupported_files,
        warnings=warnings,
        family=family,
        extraction_method=extraction_method,
        method_counts=_method_counts(documents, unsupported_files, ocr_deferred_files),
        format_counts=_format_counts(documents, failures),
        recognition_difficulty=_difficulty_counts(documents, failures),
        ocr_deferred_files=ocr_deferred_files,
    )


def extract_document_content(
    *,
    body: bytes,
    content_type: str,
    name: str,
    pdf_reader: Any = _DEFAULT_PDF_READER,
) -> ExtractedDocumentContent:
    suffix = Path(name).suffix.lower()
    normalized_type = content_type.lower().split(";", 1)[0].strip()

    if _is_pdf(normalized_type, suffix):
        return ExtractedDocumentContent(
            text=_extract_pdf_text(body, name, pdf_reader),
            file_format="pdf_text_layer",
            extraction_method="pdf_text_layer",
            recognition_difficulty="moderate",
        )

    if suffix == ".docx" or normalized_type.endswith("wordprocessingml.document"):
        return ExtractedDocumentContent(_extract_docx_text(body, name), "docx", "ooxml_docx_text", "moderate")

    if suffix == ".xlsx" or normalized_type.endswith("spreadsheetml.sheet"):
        return ExtractedDocumentContent(_extract_xlsx_text(body, name), "xlsx", "ooxml_xlsx_text", "moderate")

    if suffix == ".pptx" or normalized_type.endswith("presentationml.presentation"):
        return ExtractedDocumentContent(_extract_pptx_text(body, name), "pptx", "ooxml_pptx_text", "moderate")

    if is_image(normalized_type, suffix):
        try:
            text = extract_image_text(body, name)
        except ImageOcrIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty="hard", ocr_deferred=True) from error
        return ExtractedDocumentContent(text, "image_ocr", "tesseract_image_ocr", "hard")

    if is_video_transcript(normalized_type, suffix):
        try:
            text = clean_video_transcript(body, name)
        except ValueError as error:
            raise DocumentExtractionIssue(str(error), recognition_difficulty="hard") from error
        return ExtractedDocumentContent(text, "video_transcript", "utf8_video_transcript", "moderate")

    if is_video_media(normalized_type, suffix):
        raise DocumentExtractionIssue(
            f"{name} requires a transcript/subtitle file or an approved video media processor before scanning.",
            recognition_difficulty="hard",
            ocr_deferred=True,
        )

    if _is_text_like(normalized_type, suffix):
        return ExtractedDocumentContent(
            text=body.decode("utf-8", errors="ignore"),
            file_format=suffix.lstrip(".") or "text",
            extraction_method="utf8_text",
            recognition_difficulty="easy",
        )

    raise DocumentExtractionIssue(f"{name} is not a supported text-like file.")


def _method_counts(documents: list[SourceDocument], unsupported_files: int, ocr_deferred_files: int) -> list[dict[str, Any]]:
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


def _format_counts(documents: list[SourceDocument], failure_difficulties: list[str]) -> list[dict[str, Any]]:
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


def _difficulty_counts(documents: list[SourceDocument], failure_difficulties: list[str]) -> dict[str, int]:
    counts = {level: 0 for level in DIFFICULTY_LEVELS}
    for document in documents:
        counts[document.recognition_difficulty] = counts.get(document.recognition_difficulty, 0) + 1
    for difficulty in failure_difficulties:
        key = "hard" if difficulty == "ocr_deferred" else difficulty
        counts[key] = counts.get(key, 0) + 1
    return counts


def _is_pdf(content_type: str, suffix: str) -> bool:
    return content_type in PDF_CONTENT_TYPES or suffix in SUPPORTED_PDF_SUFFIXES


def _is_text_like(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_TEXT_SUFFIXES or any(content_type.startswith(prefix) for prefix in TEXT_CONTENT_TYPES)


def _extract_pdf_text(body: bytes, name: str, pdf_reader: Any) -> str:
    reader_cls = PdfReader if pdf_reader is _DEFAULT_PDF_READER else pdf_reader
    if reader_cls is None:
        raise DocumentExtractionIssue(f"{name} is a PDF, but PDF text extraction is not installed on this host.")

    try:
        reader = reader_cls(BytesIO(body), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise DocumentExtractionIssue(f"{name} PDF text extraction failed.", recognition_difficulty="hard") from error

    if not text.strip():
        raise DocumentExtractionIssue(
            f"{name} has no extractable PDF text layer; OCR is not enabled in prelaunch.",
            recognition_difficulty="hard",
            ocr_deferred=True,
        )

    return text


def _extract_docx_text(body: bytes, name: str) -> str:
    parts = _read_ooxml_parts(body, name, _is_docx_text_part)
    return _extract_text_tags(parts, name)


def _extract_pptx_text(body: bytes, name: str) -> str:
    parts = _read_ooxml_parts(body, name, _is_pptx_text_part)
    return _extract_text_tags(parts, name)


def _extract_xlsx_text(body: bytes, name: str) -> str:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_ooxml_budget(archive, name)
            shared_strings = _xlsx_shared_strings(archive, name)
            fragments: list[str] = []
            for part_name in _matching_members(archive, _is_xlsx_sheet_part):
                fragments.extend(_xlsx_sheet_text(archive.read(part_name), shared_strings, name))
    except (BadZipFile, LargeZipFile) as error:
        raise DocumentExtractionIssue(f"{name} is not a readable Office Open XML package.") from error

    return _joined_text(fragments, name)


def _read_ooxml_parts(body: bytes, name: str, predicate: Any) -> list[bytes]:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_ooxml_budget(archive, name)
            return [archive.read(part_name) for part_name in _matching_members(archive, predicate)]
    except (BadZipFile, LargeZipFile) as error:
        raise DocumentExtractionIssue(f"{name} is not a readable Office Open XML package.") from error


def _validate_ooxml_budget(archive: ZipFile, name: str) -> None:
    total = 0
    for info in archive.infolist():
        if info.is_dir() or not info.filename.endswith(".xml"):
            continue
        if info.file_size > MAX_OOXML_MEMBER_BYTES:
            raise DocumentExtractionIssue(f"{name} has an Office XML part over the prelaunch extraction limit.")
        total += info.file_size
        if total > MAX_OOXML_XML_BYTES:
            raise DocumentExtractionIssue(f"{name} exceeds the prelaunch Office XML extraction limit.")


def _matching_members(archive: ZipFile, predicate: Any) -> list[str]:
    return sorted(info.filename for info in archive.infolist() if not info.is_dir() and predicate(info.filename))


def _is_docx_text_part(filename: str) -> bool:
    return filename == "word/document.xml" or (
        filename.startswith("word/")
        and filename.endswith(".xml")
        and Path(filename).name.startswith(("header", "footer", "footnotes", "endnotes", "comments"))
    )


def _is_pptx_text_part(filename: str) -> bool:
    return (
        filename.startswith("ppt/slides/slide")
        or filename.startswith("ppt/notesSlides/notesSlide")
    ) and filename.endswith(".xml")


def _is_xlsx_sheet_part(filename: str) -> bool:
    return filename.startswith("xl/worksheets/sheet") and filename.endswith(".xml")


def _extract_text_tags(parts: list[bytes], name: str) -> str:
    fragments: list[str] = []
    for xml_bytes in parts:
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError as error:
            raise DocumentExtractionIssue(f"{name} contains malformed Office XML.") from error
        fragments.extend(element.text or "" for element in root.iter() if _local_name(element.tag) == "t")
    return _joined_text(fragments, name)


def _xlsx_shared_strings(archive: ZipFile, name: str) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except ElementTree.ParseError as error:
        raise DocumentExtractionIssue(f"{name} contains malformed shared strings.") from error

    values: list[str] = []
    for item in root:
        if _local_name(item.tag) != "si":
            continue
        values.append("".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t"))
    return values


def _xlsx_sheet_text(xml_bytes: bytes, shared_strings: list[str], name: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as error:
        raise DocumentExtractionIssue(f"{name} contains malformed worksheet XML.") from error

    values: list[str] = []
    for cell in root.iter():
        if _local_name(cell.tag) != "c":
            continue
        cell_type = cell.attrib.get("t")
        if cell_type == "s":
            index_text = _first_child_text(cell, "v")
            if index_text and index_text.isdigit():
                index = int(index_text)
                if index < len(shared_strings):
                    values.append(shared_strings[index])
        elif cell_type == "inlineStr":
            values.append("".join(node.text or "" for node in cell.iter() if _local_name(node.tag) == "t"))
        else:
            value = _first_child_text(cell, "v")
            if value:
                values.append(value)
    return values


def _first_child_text(element: ElementTree.Element, local_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == local_name:
            return child.text
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _joined_text(fragments: list[str], name: str) -> str:
    text = "\n".join(fragment.strip() for fragment in fragments if fragment and fragment.strip())
    if not text:
        raise DocumentExtractionIssue(f"{name} has no extractable Office text.", recognition_difficulty="hard")
    return text[:MAX_EXTRACTED_TEXT_CHARS]
