"""Temporary document readers for prelaunch source scans."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .google_drive_file_client import DriveAccessIssue, DriveFileClient, GOOGLE_FOLDER_MIME
from .source_format_recognition import DOWNLOAD_ACCEPT_HEADER, SUPPORTED_PDF_SUFFIXES, SUPPORTED_SUFFIXES, DocumentExtractionIssue, PdfReader as DefaultPdfReader, SourceDocument, SourceDocumentBatch, build_document_batch, extract_document_content
from .source_media_recognition import is_video_media
from .source_size_limits import MAX_DOCUMENT_BYTES, MAX_SOURCE_FILES, MAX_VIDEO_BYTES, extraction_limit_warning, max_bytes_for_file

PdfReader = DefaultPdfReader
GOOGLE_DRIVE_SHARE_HOSTS = {"drive.google.com", "docs.google.com"}
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"


class SourceReadIssue(Exception):
    def __init__(
        self,
        detail: str,
        pointer: str = "#/sourceId",
        *,
        recognition_difficulty: str = "unsupported",
        ocr_deferred: bool = False,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.pointer = pointer
        self.recognition_difficulty = recognition_difficulty
        self.ocr_deferred = ocr_deferred


def read_source_documents(source: dict[str, Any], scan_payload: dict[str, Any]) -> SourceDocumentBatch:
    source_type = source.get("sourceType")

    if source_type == "local_repo":
        return _read_local_source(source)

    if source_type == "remote_file_link":
        return _read_remote_link_source(source)

    if source_type == "google_drive_selection":
        token = _google_drive_access_token(scan_payload)
        if not token:
            raise SourceReadIssue("Google Drive scans require a short-lived access token.", "#/authorization/googleDriveAccessToken")
        return _read_google_drive_source(source, token)

    raise SourceReadIssue("Prelaunch mode cannot scan this source type.")


def validate_remote_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SourceReadIssue("Remote file links must use HTTPS.", "#/config/url")
    if parsed.username or parsed.password:
        raise SourceReadIssue("Remote file links must not contain credentials.", "#/config/url")
    if not parsed.hostname:
        raise SourceReadIssue("Remote file link host is required.", "#/config/url")
    if parsed.hostname.lower() in GOOGLE_DRIVE_SHARE_HOSTS:
        raise SourceReadIssue("Google Drive share links must be added through the Google Drive Picker, not Direct link.", "#/config/url")
    _validate_public_host(parsed.hostname)


def _read_local_source(source: dict[str, Any]) -> SourceDocumentBatch:
    root = Path((source.get("config") or {}).get("rootPath", "")).expanduser()
    files = [candidate for candidate in root.rglob("*") if candidate.is_file()] if root.is_dir() else []
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    failure_difficulties: list[str] = []
    unsupported = 0
    ocr_deferred = 0
    total_bytes = 0

    if len(files) > MAX_SOURCE_FILES:
        warnings.append(f"Local source scan stopped at the prelaunch {MAX_SOURCE_FILES} file limit.")

    for file_path in files[:MAX_SOURCE_FILES]:
        size = file_path.stat().st_size
        total_bytes += size
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            unsupported += 1
            failure_difficulties.append("unsupported")
            continue
        if size > _max_bytes_for_file("", file_path.name):
            unsupported += 1
            deferred = is_video_media("", file_path.suffix.lower())
            ocr_deferred += 1 if deferred else 0
            failure_difficulties.append("ocr_deferred" if deferred else "unsupported")
            continue
        try:
            documents.append(_document_from_bytes(
                body=file_path.read_bytes(),
                content_type="application/pdf" if file_path.suffix.lower() in SUPPORTED_PDF_SUFFIXES else "text/plain",
                family="Local_Source",
                name=file_path.name,
                source_path=str(file_path),
            ))
        except SourceReadIssue as issue:
            unsupported += 1
            ocr_deferred += 1 if issue.ocr_deferred else 0
            failure_difficulties.append("ocr_deferred" if issue.ocr_deferred else issue.recognition_difficulty)
            warnings.append(issue.detail)

    return build_document_batch(
        documents=documents,
        total_files=len(files),
        total_bytes=total_bytes,
        unsupported_files=unsupported,
        warnings=warnings + _unsupported_warnings(unsupported),
        family="Local_Source",
        extraction_method="local_mixed_text",
        ocr_deferred_files=ocr_deferred,
        failure_difficulties=failure_difficulties,
    )


def _read_remote_link_source(source: dict[str, Any]) -> SourceDocumentBatch:
    config = source.get("config") or {}
    url = str(config.get("url") or "")
    validate_remote_source_url(url)
    body, content_type, final_url = _download_url(url)
    name = str(config.get("fileName") or Path(urlparse(final_url).path).name or source["name"])

    if len(body) > _max_bytes_for_file(content_type, name):
        video_media = is_video_media(content_type, Path(name).suffix.lower())
        return _unsupported_batch(
            "Remote_File",
            len(body),
            "Remote video media requires an approved video processor before scanning." if video_media else extraction_limit_warning(name, content_type),
            recognition_difficulty="hard" if video_media else "unsupported",
            ocr_deferred=video_media,
        )

    try:
        document = _document_from_bytes(
            body=body,
            content_type=content_type,
            family="Remote_File",
            name=name,
            source_path=final_url,
        )
    except SourceReadIssue as issue:
        return _unsupported_batch(
            "Remote_File",
            len(body),
            issue.detail,
            recognition_difficulty=issue.recognition_difficulty,
            ocr_deferred=issue.ocr_deferred,
        )

    if not document.text:
        return _unsupported_batch("Remote_File", len(body), "Remote file MIME type is not supported for text extraction.")

    return build_document_batch(
        documents=[document],
        total_files=1,
        total_bytes=len(body),
        unsupported_files=0,
        warnings=[],
        family="Remote_File",
        extraction_method="remote_https_text",
    )


def _read_google_drive_source(source: dict[str, Any], access_token: str) -> SourceDocumentBatch:
    items = (source.get("config") or {}).get("items")
    if not isinstance(items, list) or not items:
        raise SourceReadIssue("Google Drive source requires selected files or folders.", "#/config/items")

    client = DriveFileClient(access_token, MAX_SOURCE_FILES, max(MAX_DOCUMENT_BYTES, MAX_VIDEO_BYTES))
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    failure_difficulties: list[str] = []
    total_files = 0
    total_bytes = 0
    unsupported = 0
    ocr_deferred = 0

    for item in items:
        if len(documents) + unsupported >= MAX_SOURCE_FILES:
            warnings.append("Google Drive scan stopped at the prelaunch 500 file limit.")
            break
        file_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(file_id, str) or not file_id:
            unsupported += 1
            failure_difficulties.append("unsupported")
            continue
        try:
            metadata_items = client.iter_item(file_id)
        except DriveAccessIssue as issue:
            unsupported += 1
            failure_difficulties.append("unsupported")
            warnings.append(issue.detail)
            continue
        for metadata in metadata_items:
            if len(documents) + unsupported >= MAX_SOURCE_FILES:
                warnings.append("Google Drive scan stopped at the prelaunch 500 file limit.")
                break
            total_files += 1
            try:
                document = _document_from_drive_metadata(client, metadata)
            except DriveAccessIssue as issue:
                unsupported += 1
                failure_difficulties.append("unsupported")
                warnings.append(issue.detail)
                continue
            except SourceReadIssue as issue:
                unsupported += 1
                ocr_deferred += 1 if issue.ocr_deferred else 0
                failure_difficulties.append("ocr_deferred" if issue.ocr_deferred else issue.recognition_difficulty)
                warnings.append(issue.detail)
                continue
            total_bytes += document.size_bytes
            documents.append(document)

    warnings.extend(_unsupported_warnings(unsupported))
    return build_document_batch(
        documents=documents,
        total_files=total_files,
        total_bytes=total_bytes,
        unsupported_files=unsupported,
        warnings=warnings,
        family="Google_Drive",
        extraction_method="google_drive_export",
        ocr_deferred_files=ocr_deferred,
        failure_difficulties=failure_difficulties,
    )


def _document_from_drive_metadata(client: DriveFileClient, metadata: dict[str, Any]) -> SourceDocument:
    mime_type = str(metadata.get("mimeType") or "")
    name = str(metadata.get("name") or metadata.get("id") or "Google Drive file")
    if mime_type == GOOGLE_FOLDER_MIME:
        raise SourceReadIssue("Google Drive folders are inventory containers, not text documents.")

    declared_size = _declared_size(metadata)
    if declared_size and declared_size > _max_bytes_for_file(mime_type, name):
        video_media = is_video_media(mime_type, Path(name).suffix.lower())
        raise SourceReadIssue(
            f"{name} requires a smaller bounded video sample before scanning." if video_media else extraction_limit_warning(name, mime_type),
            recognition_difficulty="hard" if video_media else "unsupported",
            ocr_deferred=video_media,
        )

    export_profile = _google_workspace_export_profile(mime_type)
    if export_profile:
        content_type = export_profile["contentType"]
        body = client.export(str(metadata["id"]), content_type)
    else:
        content_type = mime_type
        body = client.download(str(metadata["id"]))

    if len(body) > _max_bytes_for_file(content_type, name):
        video_media = is_video_media(content_type, Path(name).suffix.lower())
        raise SourceReadIssue(
            f"{name} requires an approved video processor before scanning." if video_media else extraction_limit_warning(name, content_type),
            recognition_difficulty="hard" if video_media else "unsupported",
            ocr_deferred=video_media,
        )

    document = _document_from_bytes(
        body=body,
        content_type=content_type,
        family="Google_Drive",
        name=name,
        source_path=str(metadata.get("webViewLink") or f"google-drive://{metadata['id']}"),
    )
    return _with_google_workspace_profile(document, export_profile) if export_profile else document


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        validate_remote_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_url(url: str) -> tuple[bytes, str, str]:
    request = Request(url, headers={"Accept": DOWNLOAD_ACCEPT_HEADER, "User-Agent": "DataSentinelPrelaunch/0.1"})
    try:
        with build_opener(SafeRedirectHandler()).open(request, timeout=15) as response:
            final_url = response.geturl()
            validate_remote_source_url(final_url)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            name = Path(urlparse(final_url).path).name
            return response.read(_max_bytes_for_file(content_type, name) + 1), content_type, final_url
    except HTTPError as error:
        raise SourceReadIssue(f"Remote file returned HTTP {error.code}.", "#/config/url") from error
    except URLError as error:
        raise SourceReadIssue("Remote file could not be reached safely.", "#/config/url") from error


def _google_drive_access_token(scan_payload: dict[str, Any]) -> str | None:
    authorization = scan_payload.get("authorization")
    token = authorization.get("googleDriveAccessToken") if isinstance(authorization, dict) else None
    return token.strip() if isinstance(token, str) and token.strip() else None


def _document_from_bytes(
    *,
    body: bytes,
    content_type: str,
    family: str,
    name: str,
    source_path: str,
) -> SourceDocument:
    try:
        extracted = extract_document_content(body=body, content_type=content_type, name=name, pdf_reader=PdfReader)
    except DocumentExtractionIssue as issue:
        raise SourceReadIssue(
            issue.detail,
            recognition_difficulty=issue.recognition_difficulty,
            ocr_deferred=issue.ocr_deferred,
        ) from issue

    return SourceDocument(
        name=name,
        source_path=source_path,
        text=extracted.text,
        size_bytes=len(body),
        family=family,
        file_format=extracted.file_format,
        extraction_method=extracted.extraction_method,
        recognition_difficulty=extracted.recognition_difficulty,
        text_locations=extracted.text_locations,
        warnings=extracted.warnings,
        ocr_deferred=extracted.ocr_deferred,
    )


def _google_workspace_export_profile(mime_type: str) -> dict[str, str] | None:
    if mime_type == GOOGLE_DOC_MIME:
        return {
            "contentType": "text/plain",
            "fileFormat": "google_docs_export",
            "extractionMethod": "google_docs_plain_text_export",
            "label": "Google Docs export text",
        }
    if mime_type == GOOGLE_SHEET_MIME:
        return {
            "contentType": "text/csv",
            "fileFormat": "google_sheets_export",
            "extractionMethod": "google_sheets_csv_export",
            "label": "Google Sheets CSV export",
        }
    if mime_type == GOOGLE_SLIDES_MIME:
        return {
            "contentType": "text/plain",
            "fileFormat": "google_slides_export",
            "extractionMethod": "google_slides_plain_text_export",
            "label": "Google Slides export text",
        }
    if mime_type.startswith("application/vnd.google-apps."):
        raise SourceReadIssue("This Google Workspace file type is not supported by the prelaunch scanner.")
    return None


def _with_google_workspace_profile(document: SourceDocument, profile: dict[str, str]) -> SourceDocument:
    return SourceDocument(
        name=document.name,
        source_path=document.source_path,
        text=document.text,
        size_bytes=document.size_bytes,
        family=document.family,
        file_format=profile["fileFormat"],
        extraction_method=profile["extractionMethod"],
        recognition_difficulty=document.recognition_difficulty,
        text_locations=_workspace_export_locations(document.text_locations, profile),
        warnings=document.warnings,
        ocr_deferred=document.ocr_deferred,
    )


def _workspace_export_locations(locations: tuple[dict[str, Any], ...], profile: dict[str, str]) -> tuple[dict[str, Any], ...]:
    updated = []
    for location in locations:
        next_location = dict(location)
        next_location["format"] = profile["fileFormat"]
        if not next_location.get("label") or next_location.get("label") == "Text content":
            next_location["label"] = profile["label"]
        updated.append(next_location)
    return tuple(updated)


def _unsupported_batch(
    family: str,
    total_bytes: int,
    warning: str,
    *,
    recognition_difficulty: str = "unsupported",
    ocr_deferred: bool = False,
) -> SourceDocumentBatch:
    return build_document_batch(
        documents=[],
        total_files=1,
        total_bytes=total_bytes,
        unsupported_files=1,
        warnings=[warning],
        family=family,
        extraction_method="unsupported",
        ocr_deferred_files=1 if ocr_deferred else 0,
        failure_difficulties=["ocr_deferred" if ocr_deferred else recognition_difficulty],
    )


def _unsupported_warnings(count: int) -> list[str]:
    return [f"{count} unsupported files skipped by the prelaunch scanner."] if count else []


def _max_bytes_for_file(content_type: str, name: str) -> int:
    return max_bytes_for_file(content_type, name)


def _declared_size(metadata: dict[str, Any]) -> int | None:
    try:
        return int(str(metadata.get("size") or ""))
    except ValueError:
        return None


def _validate_public_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as error:
        raise SourceReadIssue("Remote file host cannot be resolved.", "#/config/url") from error

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise SourceReadIssue("Remote file host must resolve to a public address.", "#/config/url")
