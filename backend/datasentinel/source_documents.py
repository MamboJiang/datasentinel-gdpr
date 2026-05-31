"""Temporary document readers for prelaunch source scans."""

from __future__ import annotations

from io import BytesIO
import ipaddress
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - exercised when optional runtime dependency is absent
    PdfReader = None  # type: ignore[assignment]

SUPPORTED_TEXT_SUFFIXES = {".txt", ".csv", ".tsv", ".json", ".md", ".log", ".xml", ".html"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_SUFFIXES = SUPPORTED_TEXT_SUFFIXES | SUPPORTED_PDF_SUFFIXES
TEXT_CONTENT_TYPES = {"text/", "application/json", "application/xml", "application/x-ndjson"}
PDF_CONTENT_TYPES = {"application/pdf"}
MAX_DOCUMENT_BYTES = 1_000_000
MAX_SOURCE_FILES = 500
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_API_BASE = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_SHARE_HOSTS = {"drive.google.com", "docs.google.com"}


@dataclass(frozen=True)
class SourceDocument:
    name: str
    source_path: str
    text: str
    size_bytes: int
    family: str


@dataclass(frozen=True)
class SourceDocumentBatch:
    documents: list[SourceDocument]
    total_files: int
    total_bytes: int
    unsupported_files: int
    warnings: list[str]
    family: str
    extraction_method: str


class SourceReadIssue(Exception):
    def __init__(self, detail: str, pointer: str = "#/sourceId") -> None:
        super().__init__(detail)
        self.detail = detail
        self.pointer = pointer


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
    unsupported = 0
    total_bytes = 0

    for file_path in files[:MAX_SOURCE_FILES]:
        size = file_path.stat().st_size
        total_bytes += size
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES or size > MAX_DOCUMENT_BYTES:
            unsupported += 1
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
            warnings.append(issue.detail)

    return SourceDocumentBatch(
        documents=documents,
        total_files=len(files),
        total_bytes=total_bytes,
        unsupported_files=unsupported,
        warnings=warnings + _unsupported_warnings(unsupported),
        family="Local_Source",
        extraction_method="local_mixed_text",
    )


def _read_remote_link_source(source: dict[str, Any]) -> SourceDocumentBatch:
    config = source.get("config") or {}
    url = str(config.get("url") or "")
    validate_remote_source_url(url)
    body, content_type, final_url = _download_url(url)
    name = str(config.get("fileName") or Path(urlparse(final_url).path).name or source["name"])

    if len(body) > MAX_DOCUMENT_BYTES:
        return _unsupported_batch("Remote_File", len(body), "Remote file exceeds the prelaunch 1 MB text extraction limit.")

    try:
        document = _document_from_bytes(
            body=body,
            content_type=content_type,
            family="Remote_File",
            name=name,
            source_path=final_url,
        )
    except SourceReadIssue as issue:
        return _unsupported_batch("Remote_File", len(body), issue.detail)

    if not document.text:
        return _unsupported_batch("Remote_File", len(body), "Remote file MIME type is not supported for text extraction.")

    return SourceDocumentBatch(
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

    client = DriveClient(access_token)
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    total_files = 0
    total_bytes = 0
    unsupported = 0

    for item in items:
        if len(documents) + unsupported >= MAX_SOURCE_FILES:
            warnings.append("Google Drive scan stopped at the prelaunch 500 file limit.")
            break
        file_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(file_id, str) or not file_id:
            unsupported += 1
            continue
        for metadata in client.iter_item(file_id):
            if len(documents) + unsupported >= MAX_SOURCE_FILES:
                warnings.append("Google Drive scan stopped at the prelaunch 500 file limit.")
                break
            total_files += 1
            try:
                document = client.read_text_document(metadata)
            except SourceReadIssue as issue:
                unsupported += 1
                warnings.append(issue.detail)
                continue
            total_bytes += document.size_bytes
            documents.append(document)

    warnings.extend(_unsupported_warnings(unsupported))
    return SourceDocumentBatch(
        documents=documents,
        total_files=total_files,
        total_bytes=total_bytes,
        unsupported_files=unsupported,
        warnings=warnings,
        family="Google_Drive",
        extraction_method="google_drive_export",
    )


class DriveClient:
    def __init__(self, access_token: str) -> None:
        self.access_token = access_token

    def iter_item(self, file_id: str) -> list[dict[str, Any]]:
        metadata = self._metadata(file_id)
        if metadata.get("mimeType") != GOOGLE_FOLDER_MIME:
            return [metadata]

        descendants: list[dict[str, Any]] = []
        pending = [file_id]
        while pending and len(descendants) < MAX_SOURCE_FILES:
            folder_id = pending.pop(0)
            for child in self._children(folder_id):
                if child.get("mimeType") == GOOGLE_FOLDER_MIME:
                    pending.append(str(child["id"]))
                else:
                    descendants.append(child)
                if len(descendants) >= MAX_SOURCE_FILES:
                    break
        return descendants

    def read_text_document(self, metadata: dict[str, Any]) -> SourceDocument:
        mime_type = str(metadata.get("mimeType") or "")
        name = str(metadata.get("name") or metadata.get("id") or "Google Drive file")
        if mime_type == GOOGLE_FOLDER_MIME:
            raise SourceReadIssue("Google Drive folders are inventory containers, not text documents.")

        if mime_type.startswith("application/vnd.google-apps."):
            content_type = _export_mime_type(mime_type)
            body = self._export(str(metadata["id"]), content_type)
        else:
            content_type = mime_type
            body = self._download(str(metadata["id"]))

        if len(body) > MAX_DOCUMENT_BYTES:
            raise SourceReadIssue(f"{name} exceeds the prelaunch 1 MB text extraction limit.")

        return _document_from_bytes(
            body=body,
            content_type=content_type,
            family="Google_Drive",
            name=name,
            source_path=str(metadata.get("webViewLink") or f"google-drive://{metadata['id']}"),
        )

    def _metadata(self, file_id: str) -> dict[str, Any]:
        query = urlencode({"fields": "id,name,mimeType,size,webViewLink", "supportsAllDrives": "true"})
        return self._json(f"{GOOGLE_API_BASE}/{file_id}?{query}")

    def _children(self, folder_id: str) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        page_token: str | None = None
        while len(children) < MAX_SOURCE_FILES:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken,files(id,name,mimeType,size,webViewLink)",
                "pageSize": str(min(100, MAX_SOURCE_FILES - len(children))),
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                **({"pageToken": page_token} if page_token else {}),
            }
            payload = self._json(f"{GOOGLE_API_BASE}?{urlencode(params)}")
            children.extend(list(payload.get("files") or []))
            next_page_token = payload.get("nextPageToken")
            if not isinstance(next_page_token, str) or not next_page_token:
                break
            page_token = next_page_token
        return children

    def _download(self, file_id: str) -> bytes:
        return self._bytes(f"{GOOGLE_API_BASE}/{file_id}?alt=media&supportsAllDrives=true")

    def _export(self, file_id: str, mime_type: str) -> bytes:
        return self._bytes(f"{GOOGLE_API_BASE}/{file_id}/export?{urlencode({'mimeType': mime_type})}")

    def _json(self, url: str) -> dict[str, Any]:
        try:
            return json.loads(self._bytes(url).decode("utf-8"))
        except json.JSONDecodeError as error:
            raise SourceReadIssue("Google Drive returned an invalid metadata response.") from error

    def _bytes(self, url: str) -> bytes:
        request = Request(url, headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"})
        try:
            with build_opener().open(request, timeout=20) as response:
                return response.read(MAX_DOCUMENT_BYTES + 1)
        except HTTPError as error:
            raise SourceReadIssue(f"Google Drive access failed with HTTP {error.code}.") from error
        except URLError as error:
            raise SourceReadIssue("Google Drive access failed before content extraction.") from error


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        validate_remote_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_url(url: str) -> tuple[bytes, str, str]:
    request = Request(url, headers={"Accept": "text/*, application/json, application/xml;q=0.9, */*;q=0.1", "User-Agent": "DataSentinelPrelaunch/0.1"})
    try:
        with build_opener(SafeRedirectHandler()).open(request, timeout=15) as response:
            final_url = response.geturl()
            validate_remote_source_url(final_url)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            return response.read(MAX_DOCUMENT_BYTES + 1), content_type, final_url
    except HTTPError as error:
        raise SourceReadIssue(f"Remote file returned HTTP {error.code}.", "#/config/url") from error
    except URLError as error:
        raise SourceReadIssue("Remote file could not be reached safely.", "#/config/url") from error


def _google_drive_access_token(scan_payload: dict[str, Any]) -> str | None:
    authorization = scan_payload.get("authorization")
    token = authorization.get("googleDriveAccessToken") if isinstance(authorization, dict) else None
    return token.strip() if isinstance(token, str) and token.strip() else None


def _content_type_supported(content_type: str) -> bool:
    return any(content_type.startswith(prefix) for prefix in TEXT_CONTENT_TYPES)


def _pdf_content_type_supported(content_type: str) -> bool:
    return content_type in PDF_CONTENT_TYPES


def _document_from_bytes(
    *,
    body: bytes,
    content_type: str,
    family: str,
    name: str,
    source_path: str,
) -> SourceDocument:
    suffix = Path(name).suffix.lower()
    if _pdf_content_type_supported(content_type) or suffix in SUPPORTED_PDF_SUFFIXES:
        text = _extract_pdf_text(body, name)
    elif _content_type_supported(content_type) or suffix in SUPPORTED_TEXT_SUFFIXES:
        text = body.decode("utf-8", errors="ignore")
    else:
        raise SourceReadIssue(f"{name} is not a supported text-like file.")

    return SourceDocument(
        name=name,
        source_path=source_path,
        text=text,
        size_bytes=len(body),
        family=family,
    )


def _extract_pdf_text(body: bytes, name: str) -> str:
    if PdfReader is None:
        raise SourceReadIssue(f"{name} is a PDF, but PDF text extraction is not installed on this host.")

    try:
        reader = PdfReader(BytesIO(body), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise SourceReadIssue(f"{name} PDF text extraction failed.") from error

    if not text.strip():
        raise SourceReadIssue(f"{name} has no extractable PDF text layer; OCR is not enabled in prelaunch.")

    return text


def _export_mime_type(mime_type: str) -> str:
    if mime_type == "application/vnd.google-apps.spreadsheet":
        return "text/csv"
    return "text/plain"


def _unsupported_batch(family: str, total_bytes: int, warning: str) -> SourceDocumentBatch:
    return SourceDocumentBatch([], 1, total_bytes, 1, [warning], family, "unsupported")


def _unsupported_warnings(count: int) -> list[str]:
    return [f"{count} unsupported files skipped by the prelaunch scanner."] if count else []


def _validate_public_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as error:
        raise SourceReadIssue("Remote file host cannot be resolved.", "#/config/url") from error

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise SourceReadIssue("Remote file host must resolve to a public address.", "#/config/url")
