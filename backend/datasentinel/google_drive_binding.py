"""Account-scoped Google Drive binding for prelaunch source scans."""

from __future__ import annotations

import copy
import json
import secrets
import time
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .auth_support import cookie_value, sign, unsign
from .envelope import envelope, problem, response, utc_now
from .google_drive_config import DRIVE_READONLY_SCOPE

DRIVE_BIND_TX_COOKIE = "datasentinel_drive_bind_tx"
DRIVE_BINDING_SCOPES = ("openid", "email", "profile", DRIVE_READONLY_SCOPE)
DRIVE_BINDING_TX_TTL_SECONDS = 10 * 60


class DriveBindingStore(Protocol):
    def get_binding(self, user_id: str) -> dict[str, Any] | None:
        """Return a Drive binding for a first-party user."""

    def upsert_binding(self, binding: dict[str, Any]) -> dict[str, Any]:
        """Create or replace a Drive binding."""

    def delete_binding(self, user_id: str) -> dict[str, Any] | None:
        """Remove a Drive binding for a first-party user."""


class InMemoryDriveBindingStore:
    def __init__(self) -> None:
        self.bindings: dict[str, dict[str, Any]] = {}

    def get_binding(self, user_id: str) -> dict[str, Any] | None:
        binding = self.bindings.get(user_id)
        return copy.deepcopy(binding) if binding else None

    def upsert_binding(self, binding: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(binding)
        self.bindings[stored["userId"]] = stored
        return copy.deepcopy(stored)

    def delete_binding(self, user_id: str) -> dict[str, Any] | None:
        binding = self.bindings.pop(user_id, None)
        return copy.deepcopy(binding) if binding else None


class GoogleDriveOAuthTransport:
    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
        data = urlencode(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method="POST")
        with urlopen(request, timeout=12) as result:
            body = result.read().decode("utf-8")
            return json.loads(body) if body else {}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=12) as result:
            return json.loads(result.read().decode("utf-8"))

    def revoke_token(self, token: str) -> bool:
        request = Request(
            f"https://oauth2.googleapis.com/revoke?{urlencode({'token': token})}",
            data=b"",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=12):
            return True


class GoogleDriveBindingService:
    def __init__(
        self,
        store: DriveBindingStore | None = None,
        settings: dict[str, Any] | None = None,
        transport: GoogleDriveOAuthTransport | None = None,
    ) -> None:
        from .auth import settings_from_env

        self.store = store or InMemoryDriveBindingStore()
        self.settings = settings or settings_from_env()
        self.transport = transport or GoogleDriveOAuthTransport()

    def status(self, user: dict[str, Any] | None, trace_id: str, path: str) -> dict[str, Any]:
        if not user:
            return self._session_required(path, trace_id)

        binding = self.store.get_binding(user["userId"])
        return response(200, envelope(_safe_binding(binding, self._configured()), trace_id), trace_id)

    def start_binding(self, user: dict[str, Any] | None, trace_id: str, path: str) -> dict[str, Any]:
        if not user:
            return self._session_required(path, trace_id)

        if not self._configured():
            return response(
                503,
                problem(
                    status=503,
                    title="Google Drive binding unavailable",
                    detail="Google OAuth client credentials are not configured.",
                    instance=path,
                    trace_id=trace_id,
                    code="google-drive-binding-unavailable",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        state = secrets.token_urlsafe(24)
        transaction = {
            "state": state,
            "userId": user["userId"],
            "exp": int(time.time()) + DRIVE_BINDING_TX_TTL_SECONDS,
        }
        location = self._authorization_url(state, user.get("email"))
        result = _redirect(location, trace_id, [self._cookie(DRIVE_BIND_TX_COOKIE, sign(transaction, self._secret()), DRIVE_BINDING_TX_TTL_SECONDS)])
        return result

    def complete_callback(
        self,
        query: dict[str, list[str]],
        headers: dict[str, str],
        user: dict[str, Any] | None,
        trace_id: str,
    ) -> dict[str, Any]:
        failure_cookies = [self._clear_cookie(DRIVE_BIND_TX_COOKIE)]
        if not user:
            return _redirect(self._return_url("failed", "session"), trace_id, failure_cookies)

        if query.get("error"):
            return _redirect(self._return_url("failed", "provider_denied"), trace_id, failure_cookies)

        code = _first(query, "code")
        state = _first(query, "state")
        transaction = self._read_transaction(headers.get("Cookie", ""))
        if not code or not state or not transaction or transaction.get("state") != state or transaction.get("userId") != user["userId"]:
            return _redirect(self._return_url("failed", "state"), trace_id, failure_cookies)

        try:
            binding = self._binding_from_code(code, user["userId"])
        except Exception:
            return _redirect(self._return_url("failed", "provider_exchange"), trace_id, failure_cookies)

        existing = self.store.get_binding(user["userId"])
        self.store.upsert_binding(binding)
        if existing and existing.get("refreshToken") != binding.get("refreshToken"):
            self._revoke_quietly(str(existing.get("refreshToken") or ""))
        return _redirect(self._return_url("success", None), trace_id, failure_cookies)

    def disconnect(self, user: dict[str, Any] | None, trace_id: str, path: str) -> dict[str, Any]:
        if not user:
            return self._session_required(path, trace_id)

        deleted = self.store.delete_binding(user["userId"])
        revoked = self._revoke_quietly(str(deleted.get("refreshToken") or "")) if deleted else False
        payload = {**_safe_binding(None, self._configured()), "revocationAttempted": bool(deleted), "revoked": revoked}
        return response(200, envelope(payload, trace_id), trace_id)

    def picker_token(self, user: dict[str, Any] | None, trace_id: str, path: str) -> dict[str, Any]:
        if not user:
            return self._session_required(path, trace_id)

        if not self._configured():
            return response(
                503,
                problem(
                    status=503,
                    title="Google Drive binding unavailable",
                    detail="Google OAuth client credentials are not configured.",
                    instance=path,
                    trace_id=trace_id,
                    code="google-drive-binding-unavailable",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        binding = self.store.get_binding(user["userId"])
        refresh_token = binding.get("refreshToken") if binding else None
        if not isinstance(refresh_token, str) or not refresh_token:
            return response(
                409,
                problem(
                    status=409,
                    title="Google Drive binding required",
                    detail="Connect Google Drive in Account settings before requesting a bound Picker token.",
                    instance=path,
                    trace_id=trace_id,
                    code="google-drive-binding-required",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        access_token = self.access_token(user)
        if not access_token:
            return response(
                502,
                problem(
                    status=502,
                    title="Google Drive token refresh failed",
                    detail="The connected Google Drive binding could not mint a Picker access token.",
                    instance=path,
                    trace_id=trace_id,
                    code="google-drive-token-refresh-failed",
                ),
                trace_id,
                content_type="application/problem+json",
            )

        return response(200, envelope({
            "accessToken": access_token,
            "provider": "google_drive",
            "scopes": binding.get("scopes") or [],
            "source": "account_binding",
            "tokenType": "Bearer",
        }, trace_id), trace_id)

    def access_token(self, user: dict[str, Any] | None) -> str | None:
        if not user:
            return None

        binding = self.store.get_binding(user["userId"])
        refresh_token = binding.get("refreshToken") if binding else None
        if not isinstance(refresh_token, str) or not refresh_token:
            return None

        try:
            token = self.transport.post_form("https://oauth2.googleapis.com/token", {
                "client_id": self._google_credentials()["client_id"],
                "client_secret": self._google_credentials()["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }, {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        except Exception:
            return None

        access_token = token.get("access_token")
        return access_token.strip() if isinstance(access_token, str) and access_token.strip() else None

    def _binding_from_code(self, code: str, user_id: str) -> dict[str, Any]:
        token = self.transport.post_form("https://oauth2.googleapis.com/token", {
            "client_id": self._google_credentials()["client_id"],
            "client_secret": self._google_credentials()["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._callback_url(),
        }, {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("missing Google access token")

        userinfo = self.transport.get_json("https://openidconnect.googleapis.com/v1/userinfo", {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        })
        subject = userinfo.get("sub")
        if not isinstance(subject, str) or not subject:
            raise ValueError("missing Google userinfo subject")

        existing = self.store.get_binding(user_id)
        refresh_token = token.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            if existing and existing.get("providerSubject") == subject and isinstance(existing.get("refreshToken"), str):
                refresh_token = existing["refreshToken"]
            else:
                raise ValueError("missing Google refresh token")

        scopes = str(token.get("scope") or " ".join(DRIVE_BINDING_SCOPES)).split()
        now = utc_now()
        return {
            "userId": user_id,
            "provider": "google_drive",
            "providerSubject": subject,
            "displayName": str(userinfo.get("name") or userinfo.get("email") or "Google Drive account"),
            "email": str(userinfo["email"]) if userinfo.get("email") else None,
            "avatarUrl": str(userinfo["picture"]) if userinfo.get("picture") else None,
            "scopes": scopes,
            "refreshToken": refresh_token,
            "connectedAt": existing.get("connectedAt") if existing else now,
            "updatedAt": now,
        }

    def _authorization_url(self, state: str, login_hint: Any) -> str:
        params = {
            "access_type": "offline",
            "client_id": self._google_credentials()["client_id"],
            "include_granted_scopes": "true",
            "prompt": "consent select_account",
            "redirect_uri": self._callback_url(),
            "response_type": "code",
            "scope": " ".join(DRIVE_BINDING_SCOPES),
            "state": state,
            **({"login_hint": str(login_hint)} if login_hint else {}),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def _callback_url(self) -> str:
        return f"{self.settings['redirect_base_url'].rstrip('/')}/api/integrations/google-drive/bind/callback"

    def _return_url(self, status: str, reason: str | None) -> str:
        params = {"driveBinding": status}
        if reason:
            params["reason"] = reason
        return f"{self.settings['frontend_return_url']}?{urlencode(params)}"

    def _configured(self) -> bool:
        credentials = self._google_credentials()
        return bool(credentials.get("client_id") and credentials.get("client_secret") and self._secret())

    def _google_credentials(self) -> dict[str, str]:
        return self.settings["providers"]["google"]

    def _read_transaction(self, cookie_header: str) -> dict[str, Any] | None:
        value = cookie_value(cookie_header, DRIVE_BIND_TX_COOKIE)
        return unsign(value, self._secret()) if value else None

    def _cookie(self, name: str, value: str, max_age: int) -> str:
        cookie = f"{name}={value}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Lax"
        return f"{cookie}; Secure" if self.settings["cookie_secure"] else cookie

    def _clear_cookie(self, name: str) -> str:
        cookie = f"{name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        return f"{cookie}; Secure" if self.settings["cookie_secure"] else cookie

    def _secret(self) -> str:
        return str(self.settings["session_secret"] or "")

    def _revoke_quietly(self, token: str) -> bool:
        if not token:
            return False
        try:
            return bool(self.transport.revoke_token(token))
        except Exception:
            return False

    def _session_required(self, path: str, trace_id: str) -> dict[str, Any]:
        return response(
            401,
            problem(
                status=401,
                title="Authentication required",
                detail="Sign in before managing a Google Drive binding.",
                instance=path,
                trace_id=trace_id,
                code="auth-required",
            ),
            trace_id,
            content_type="application/problem+json",
        )


def _safe_binding(binding: dict[str, Any] | None, configured: bool) -> dict[str, Any]:
    if not binding:
        return {"connected": False, "configured": configured, "provider": "google_drive", "scopes": []}

    return {
        "connected": True,
        "configured": configured,
        "provider": "google_drive",
        "email": binding.get("email"),
        "displayName": binding.get("displayName"),
        "avatarUrl": binding.get("avatarUrl"),
        "scopes": binding.get("scopes") or [],
        "connectedAt": binding.get("connectedAt"),
        "updatedAt": binding.get("updatedAt"),
        "tokenRefreshAvailable": bool(binding.get("refreshToken")),
        "serverSideOnly": True,
    }


def _redirect(location: str, trace_id: str, cookies: list[str]) -> dict[str, Any]:
    return {
        "status": 302,
        "contentType": "application/json",
        "headers": {"Location": location, "Set-Cookie": cookies, "X-Trace-Id": trace_id, "X-Contract-Version": "0.1.0"},
        "body": {},
    }


def _first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values else None
