from __future__ import annotations

import json
import unittest

from backend.datasentinel.auth import AUTH_TX_COOKIE, SESSION_COOKIE, AuthService, InMemoryAuthStore
from backend.datasentinel.auth_support import cookie_value, unsign
from backend.datasentinel.google_drive_binding import GoogleDriveBindingService
from backend.datasentinel.source_http import SourceHttpApp


class FakeOAuthTransport:
    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, str]:
        return {"access_token": "provider_token_not_returned", "token_type": "bearer"}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, object] | list[dict[str, object]]:
        if url.endswith("/user/emails"):
            return [{"email": "privacy.reviewer@example.org", "primary": True, "verified": True}]
        return {"id": 42, "login": "privacy-reviewer", "name": "Privacy Reviewer", "email": None, "avatar_url": "https://avatars.example/reviewer.png"}


class FakeDriveBindingTransport:
    def __init__(self) -> None:
        self.refresh_count = 0

    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, str]:
        if payload.get("grant_type") == "refresh_token":
            self.refresh_count += 1
            return {"access_token": "drive_refreshed_picker_access", "token_type": "Bearer"}
        return {}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, object]:
        return {}

    def revoke_token(self, token: str) -> bool:
        return True


def auth_settings() -> dict[str, object]:
    return {
        "auth_required": False,
        "cookie_secure": False,
        "frontend_return_url": "http://localhost:5173/dashboard",
        "redirect_base_url": "http://localhost:8000",
        "session_secret": "test-session-secret",
        "providers": {
            "google": {"client_id": "google-client", "client_secret": "google-secret"},
            "github": {"client_id": "github-client", "client_secret": "github-secret"},
        },
    }


def start_github_session(app: SourceHttpApp) -> str:
    login = app.handle("GET", "/api/auth/login/github", "trace_auth_login")
    auth_cookie = login["headers"]["Set-Cookie"][0]
    tx_value = cookie_value(auth_cookie, AUTH_TX_COOKIE)
    transaction = unsign(str(tx_value or ""), str(app.auth_service.settings["session_secret"]))
    state = transaction["state"] if transaction else ""
    callback = app.handle(
        "GET",
        f"/api/auth/callback/github?code=oauth_code&state={state}",
        "trace_auth_callback",
        None,
        None,
        {"Cookie": f"{AUTH_TX_COOKIE}={tx_value}"},
    )
    session_value = next(
        value
        for cookie in callback["headers"]["Set-Cookie"]
        if (value := cookie_value(cookie, SESSION_COOKIE))
    )
    return f"{SESSION_COOKIE}={session_value}"


class GoogleDriveBoundPickerTests(unittest.TestCase):
    def test_bound_picker_token_refreshes_without_exposing_refresh_token(self) -> None:
        auth_service = AuthService(InMemoryAuthStore(), auth_settings(), FakeOAuthTransport())
        drive_transport = FakeDriveBindingTransport()
        drive_service = GoogleDriveBindingService(settings=auth_service.settings, transport=drive_transport)
        app = SourceHttpApp(auth_service=auth_service, drive_binding_service=drive_service)
        session_cookie = start_github_session(app)
        user = auth_service.session_payload({"Cookie": session_cookie})["user"]

        drive_service.store.upsert_binding({
            "userId": user["userId"],
            "provider": "google_drive",
            "providerSubject": "google-drive-subject",
            "displayName": "Drive Reviewer",
            "email": "drive.reviewer@example.org",
            "avatarUrl": None,
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
            "refreshToken": "drive_refresh_not_returned",
            "connectedAt": "2026-05-31T00:00:00Z",
            "updatedAt": "2026-05-31T00:00:00Z",
        })

        result = app.handle("POST", "/api/integrations/google-drive/picker-token", "trace_picker_token", "{}", "application/json", {"Cookie": session_cookie})
        serialized = json.dumps(result["body"])

        self.assertEqual(result["status"], 200)
        self.assertEqual(result["body"]["data"]["accessToken"], "drive_refreshed_picker_access")
        self.assertEqual(result["body"]["data"]["source"], "account_binding")
        self.assertEqual(drive_transport.refresh_count, 1)
        self.assertNotIn("drive_refresh_not_returned", serialized)

    def test_bound_picker_token_rejects_unbound_account(self) -> None:
        auth_service = AuthService(InMemoryAuthStore(), auth_settings(), FakeOAuthTransport())
        app = SourceHttpApp(auth_service=auth_service, drive_binding_service=GoogleDriveBindingService(settings=auth_service.settings, transport=FakeDriveBindingTransport()))
        session_cookie = start_github_session(app)

        result = app.handle("POST", "/api/integrations/google-drive/picker-token", "trace_picker_token_unbound", "{}", "application/json", {"Cookie": session_cookie})

        self.assertEqual(result["status"], 409)
        self.assertEqual(result["contentType"], "application/problem+json")


if __name__ == "__main__":
    unittest.main()
