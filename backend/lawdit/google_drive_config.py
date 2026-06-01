"""Public Google Drive Picker configuration."""

from __future__ import annotations

import os
from typing import Any

from .envelope import envelope, response

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def picker_config_from_env() -> dict[str, Any]:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    api_key = os.environ.get("GOOGLE_PICKER_API_KEY", "").strip()
    app_id = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "").strip()
    return {
        "configured": bool(client_id and api_key and app_id),
        "clientId": client_id if client_id else None,
        "apiKey": api_key if api_key else None,
        "appId": app_id if app_id else None,
        "scopes": {
            "files": DRIVE_FILE_SCOPE,
            "folders": DRIVE_READONLY_SCOPE,
        },
        "missing": [
            key
            for key, value in {
                "GOOGLE_CLIENT_ID": client_id,
                "GOOGLE_PICKER_API_KEY": api_key,
                "GOOGLE_CLOUD_PROJECT_NUMBER": app_id,
            }.items()
            if not value
        ],
    }


def picker_config_response(trace_id: str) -> dict[str, Any]:
    return response(200, envelope(picker_config_from_env(), trace_id), trace_id)
