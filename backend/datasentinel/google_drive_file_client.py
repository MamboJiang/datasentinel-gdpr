"""Google Drive file metadata and byte download client."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

GOOGLE_API_BASE = "https://www.googleapis.com/drive/v3/files"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveAccessIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DriveFileClient:
    def __init__(self, access_token: str, max_files: int, max_bytes: int) -> None:
        self.access_token = access_token
        self.max_files = max_files
        self.max_bytes = max_bytes

    def iter_item(self, file_id: str) -> list[dict[str, Any]]:
        metadata = self._metadata(file_id)
        if metadata.get("mimeType") != GOOGLE_FOLDER_MIME:
            return [metadata]

        descendants: list[dict[str, Any]] = []
        pending = [file_id]
        while pending and len(descendants) < self.max_files:
            folder_id = pending.pop(0)
            for child in self._children(folder_id):
                if child.get("mimeType") == GOOGLE_FOLDER_MIME:
                    pending.append(str(child["id"]))
                else:
                    descendants.append(child)
                if len(descendants) >= self.max_files:
                    break
        return descendants

    def download(self, file_id: str) -> bytes:
        return self._bytes(f"{GOOGLE_API_BASE}/{file_id}?alt=media&supportsAllDrives=true")

    def export(self, file_id: str, mime_type: str) -> bytes:
        return self._bytes(f"{GOOGLE_API_BASE}/{file_id}/export?{urlencode({'mimeType': mime_type})}")

    def _metadata(self, file_id: str) -> dict[str, Any]:
        query = urlencode({"fields": "id,name,mimeType,size,webViewLink", "supportsAllDrives": "true"})
        return self._json(f"{GOOGLE_API_BASE}/{file_id}?{query}")

    def _children(self, folder_id: str) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        page_token: str | None = None
        while len(children) < self.max_files:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken,files(id,name,mimeType,size,webViewLink)",
                "pageSize": str(min(100, self.max_files - len(children))),
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

    def _json(self, url: str) -> dict[str, Any]:
        try:
            return json.loads(self._bytes(url).decode("utf-8"))
        except json.JSONDecodeError as error:
            raise DriveAccessIssue("Google Drive returned an invalid metadata response.") from error

    def _bytes(self, url: str) -> bytes:
        request = Request(url, headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"})
        try:
            with build_opener().open(request, timeout=20) as response:
                return response.read(self.max_bytes + 1)
        except HTTPError as error:
            raise DriveAccessIssue(f"Google Drive access failed with HTTP {error.code}.") from error
        except URLError as error:
            raise DriveAccessIssue("Google Drive access failed before content extraction.") from error
