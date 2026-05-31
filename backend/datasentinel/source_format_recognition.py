"""Bounded local format recognition for prelaunch source scans."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .source_archive_text import ArchiveExtractionIssue, SUPPORTED_ARCHIVE_SUFFIXES, extract_zip_archive_text, is_archive_like
from .source_batch_metrics import difficulty_counts, format_counts, method_counts
from .source_email_text import EmailExtractionIssue, extract_email_text
from .source_image_ocr import ImageOcrIssue, extract_image_content
from .source_json_text import JsonExtractionIssue, extract_json_text
from .source_legacy_office import (
    LEGACY_OFFICE_SUFFIXES,
    LegacyOfficeExtractionIssue,
    extract_legacy_office_text,
    is_legacy_office,
    legacy_office_format,
)
from .source_markdown_text import MarkdownExtractionIssue, extract_markdown_text
from .source_media_recognition import (
    MEDIA_ACCEPT_HEADER,
    SUPPORTED_MEDIA_SUFFIXES,
    clean_video_transcript,
    is_image,
    is_video_media,
    is_video_transcript,
)
from .source_opendocument_text import OpenDocumentExtractionIssue, extract_opendocument_text
from .source_pdf_text import PdfExtractionIssue, PdfExtractionResult, extract_pdf_content
from .source_rtf_text import RtfExtractionIssue, extract_rtf_text
from .source_structured_text import (
    StructuredExtractionIssue,
    extract_docx_text,
    extract_html_text,
    extract_pptx_text,
    extract_xml_text,
)
from .source_tabular_text import TabularExtractionIssue, extract_delimited_text, extract_xlsx_text
from .source_text_decoding import decode_text_body
from .source_text_locations import text_stream_location
from .source_video_ocr import VideoFrameOcrIssue, extract_video_frame_content

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - exercised when optional runtime dependency is absent
    PdfReader = None  # type: ignore[assignment]

SUPPORTED_TEXT_SUFFIXES = {".txt", ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".md", ".log", ".xml", ".html", ".htm", ".rtf"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx"}
SUPPORTED_OPENDOCUMENT_SUFFIXES = {".odt", ".ods", ".odp"}
SUPPORTED_EMAIL_SUFFIXES = {".eml"}
SUPPORTED_SUFFIXES = (
    SUPPORTED_TEXT_SUFFIXES
    | SUPPORTED_PDF_SUFFIXES
    | SUPPORTED_OFFICE_SUFFIXES
    | LEGACY_OFFICE_SUFFIXES
    | SUPPORTED_OPENDOCUMENT_SUFFIXES
    | SUPPORTED_EMAIL_SUFFIXES
    | SUPPORTED_ARCHIVE_SUFFIXES
    | SUPPORTED_MEDIA_SUFFIXES
)
TEXT_CONTENT_TYPES = {"text/", "application/json", "application/xml", "application/x-ndjson", "application/rtf"}
PDF_CONTENT_TYPES = {"application/pdf"}
EMAIL_CONTENT_TYPES = {"message/rfc822", "application/eml"}
OFFICE_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
LEGACY_OFFICE_ACCEPT_HEADER = "application/msword;q=0.8, application/vnd.ms-excel;q=0.8, application/vnd.ms-powerpoint;q=0.8"
OPENDOCUMENT_CONTENT_TYPES = {"application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.spreadsheet", "application/vnd.oasis.opendocument.presentation"}
OPENDOCUMENT_ACCEPT_HEADER = "application/vnd.oasis.opendocument.text;q=0.8, application/vnd.oasis.opendocument.spreadsheet;q=0.8, application/vnd.oasis.opendocument.presentation;q=0.8"
DOWNLOAD_ACCEPT_HEADER = (
    f"text/*, application/json, application/xml;q=0.9, application/rtf;q=0.9, message/rfc822;q=0.8, application/zip;q=0.8, application/pdf;q=0.8, {OPENDOCUMENT_ACCEPT_HEADER}, {LEGACY_OFFICE_ACCEPT_HEADER}, "
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document;q=0.8, "
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;q=0.8, "
    f"application/vnd.openxmlformats-officedocument.presentationml.presentation;q=0.8, {MEDIA_ACCEPT_HEADER}, */*;q=0.1"
)
MAX_OOXML_XML_BYTES = 4_000_000
MAX_OOXML_MEMBER_BYTES = 2_000_000
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
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


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
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


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
        method_counts=method_counts(documents, unsupported_files, ocr_deferred_files),
        format_counts=format_counts(documents, failures),
        recognition_difficulty=difficulty_counts(documents, failures),
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
        extracted = _extract_pdf_content(body, name, pdf_reader)
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format=extracted.file_format,
            extraction_method=extracted.extraction_method,
            recognition_difficulty=extracted.recognition_difficulty,
            text_locations=extracted.text_locations,
        )

    if suffix == ".docx" or normalized_type.endswith("wordprocessingml.document"):
        try:
            extracted = extract_docx_text(
                body,
                name,
                max_xml_bytes=MAX_OOXML_XML_BYTES,
                max_member_bytes=MAX_OOXML_MEMBER_BYTES,
            )
        except StructuredExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, "docx", "ooxml_docx_text", "moderate", text_locations=extracted.locations)

    if suffix == ".xlsx" or normalized_type.endswith("spreadsheetml.sheet"):
        try:
            extracted = extract_xlsx_text(
                body,
                name,
                max_xml_bytes=MAX_OOXML_XML_BYTES,
                max_member_bytes=MAX_OOXML_MEMBER_BYTES,
            )
        except TabularExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, "xlsx", "ooxml_xlsx_text", "moderate", text_locations=extracted.locations)

    if suffix == ".pptx" or normalized_type.endswith("presentationml.presentation"):
        try:
            extracted = extract_pptx_text(
                body,
                name,
                max_xml_bytes=MAX_OOXML_XML_BYTES,
                max_member_bytes=MAX_OOXML_MEMBER_BYTES,
            )
        except StructuredExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, "pptx", "ooxml_pptx_text", "moderate", text_locations=extracted.locations)

    if is_legacy_office(normalized_type, suffix):
        file_format = legacy_office_format(normalized_type, suffix)
        try:
            extracted = extract_legacy_office_text(body, name, file_format)
        except LegacyOfficeExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty="hard") from error
        return ExtractedDocumentContent(extracted.text, file_format, "libreoffice_legacy_office_text", "hard", text_locations=extracted.locations)

    if suffix in SUPPORTED_OPENDOCUMENT_SUFFIXES or normalized_type in OPENDOCUMENT_CONTENT_TYPES:
        file_format = _opendocument_file_format(normalized_type, suffix)
        try:
            extracted = extract_opendocument_text(
                body,
                name,
                file_format,
                max_xml_bytes=MAX_OOXML_XML_BYTES,
                max_member_bytes=MAX_OOXML_MEMBER_BYTES,
            )
        except OpenDocumentExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, file_format, extracted.extraction_method, "moderate", text_locations=extracted.locations)

    if _is_email_like(normalized_type, suffix):
        try:
            extracted = extract_email_text(body, name)
        except EmailExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, "eml", "rfc5322_mime_text", "moderate", text_locations=extracted.locations)

    if is_archive_like(normalized_type, suffix):
        try:
            extracted = extract_zip_archive_text(
                body,
                name,
                lambda member_body, member_name: extract_document_content(
                    body=member_body,
                    content_type="",
                    name=member_name,
                    pdf_reader=pdf_reader,
                ),
            )
        except ArchiveExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(extracted.text, "zip", "zip_member_text", "moderate", text_locations=extracted.locations)

    if is_image(normalized_type, suffix):
        try:
            extracted = extract_image_content(body, name)
        except ImageOcrIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty="hard", ocr_deferred=True) from error
        return ExtractedDocumentContent(extracted.text, "image_ocr", "tesseract_image_ocr", "hard", text_locations=extracted.text_locations)

    if is_video_transcript(normalized_type, suffix):
        try:
            text = clean_video_transcript(body, name)
        except ValueError as error:
            raise DocumentExtractionIssue(str(error), recognition_difficulty="hard") from error
        return ExtractedDocumentContent(text, "video_transcript", "utf8_video_transcript", "moderate", text_locations=text_stream_location(text, "video_transcript", "Transcript text"))

    if is_video_media(normalized_type, suffix):
        try:
            extracted = extract_video_frame_content(body, name)
        except VideoFrameOcrIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty="hard", ocr_deferred=True) from error
        return ExtractedDocumentContent(extracted.text, "video_ocr", "ffmpeg_frame_tesseract_ocr", "hard", text_locations=extracted.text_locations)

    if suffix in {".csv", ".tsv"} or normalized_type in {"text/csv", "text/tab-separated-values"}:
        file_format = "tsv" if suffix == ".tsv" or normalized_type == "text/tab-separated-values" else "csv"
        delimiter = "\t" if file_format == "tsv" else ","
        extracted = extract_delimited_text(body, name, delimiter=delimiter, file_format=file_format, content_type=content_type)
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format=file_format,
            extraction_method="utf8_text",
            recognition_difficulty="easy",
            text_locations=extracted.locations,
        )

    if suffix in {".html", ".htm"} or normalized_type == "text/html":
        try:
            extracted = extract_html_text(body, name, "html", content_type=content_type)
        except StructuredExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format="html",
            extraction_method="html_text",
            recognition_difficulty="easy",
            text_locations=extracted.locations,
        )

    if suffix == ".md" or normalized_type in {"text/markdown", "text/x-markdown"}:
        try:
            extracted = extract_markdown_text(body, name, content_type=content_type)
        except MarkdownExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format="markdown",
            extraction_method="markdown_text",
            recognition_difficulty="easy",
            text_locations=extracted.locations,
        )

    if _is_xml_like(normalized_type, suffix):
        try:
            extracted = extract_xml_text(body, name, content_type=content_type)
        except StructuredExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format="xml",
            extraction_method="xml_structure_text",
            recognition_difficulty="easy",
            text_locations=extracted.locations,
        )

    if _is_rtf_like(normalized_type, suffix):
        try:
            extracted = extract_rtf_text(body, name)
        except RtfExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format="rtf",
            extraction_method="rtf_text",
            recognition_difficulty="moderate",
            text_locations=text_stream_location(extracted.text, "rtf", "RTF text"),
        )

    if _is_json_like(normalized_type, suffix):
        file_format = _json_file_format(normalized_type, suffix)
        try:
            extracted = extract_json_text(body, name, file_format, content_type=content_type)
        except JsonExtractionIssue as error:
            raise DocumentExtractionIssue(error.detail, recognition_difficulty=error.recognition_difficulty) from error
        return ExtractedDocumentContent(
            text=extracted.text,
            file_format=file_format,
            extraction_method="json_structure_text",
            recognition_difficulty="easy",
            text_locations=extracted.locations,
        )

    if _is_text_like(normalized_type, suffix):
        text = decode_text_body(body, content_type)
        file_format = suffix.lstrip(".") or "text"
        return ExtractedDocumentContent(
            text=text,
            file_format=file_format,
            extraction_method="utf8_text",
            recognition_difficulty="easy",
            text_locations=text_stream_location(text, file_format, "Text content"),
        )

    raise DocumentExtractionIssue(f"{name} is not a supported text-like file.")


def _is_pdf(content_type: str, suffix: str) -> bool:
    return content_type in PDF_CONTENT_TYPES or suffix in SUPPORTED_PDF_SUFFIXES


def _is_text_like(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_TEXT_SUFFIXES or any(content_type.startswith(prefix) for prefix in TEXT_CONTENT_TYPES)


def _is_json_like(content_type: str, suffix: str) -> bool:
    return suffix in {".json", ".jsonl", ".ndjson"} or content_type in {"application/json", "application/x-ndjson"}


def _is_xml_like(content_type: str, suffix: str) -> bool:
    return suffix == ".xml" or content_type in {"application/xml", "text/xml"}


def _is_rtf_like(content_type: str, suffix: str) -> bool:
    return suffix == ".rtf" or content_type in {"application/rtf", "text/rtf", "application/x-rtf"}


def _is_email_like(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_EMAIL_SUFFIXES or content_type in EMAIL_CONTENT_TYPES


def _json_file_format(content_type: str, suffix: str) -> str:
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".ndjson" or content_type == "application/x-ndjson":
        return "ndjson"
    return "json"


def _opendocument_file_format(content_type: str, suffix: str) -> str:
    if suffix == ".ods" or content_type.endswith(".spreadsheet"):
        return "ods"
    if suffix == ".odp" or content_type.endswith(".presentation"):
        return "odp"
    return "odt"


def _extract_pdf_content(body: bytes, name: str, pdf_reader: Any) -> PdfExtractionResult:
    reader_cls = PdfReader if pdf_reader is _DEFAULT_PDF_READER else pdf_reader
    try:
        return extract_pdf_content(body, name, reader_cls)
    except PdfExtractionIssue as error:
        raise DocumentExtractionIssue(
            error.detail,
            recognition_difficulty=error.recognition_difficulty,
            ocr_deferred=error.ocr_deferred,
        ) from error
