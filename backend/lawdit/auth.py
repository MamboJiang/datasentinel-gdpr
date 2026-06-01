"""Prelaunch OAuth account and session boundary."""

from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from .envelope import envelope, problem, response
from .auth_support import (
    anonymous_session,
    cookie_value,
    decode_jwt_payload,
    env_bool,
    epoch_to_iso,
    first,
    pkce_challenge,
    profile,
    redirect,
    sign,
    unsign,
    validate_google_claims,
)

AUTH_TX_COOKIE = "lawdit_auth_tx"
SESSION_COOKIE = "lawdit_session"
PROVIDERS = ("google", "github")
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
TX_TTL_SECONDS = 10 * 60


class AuthStore(Protocol):
    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        """Create or update a local account profile."""

    def create_session(self, user_id: str, expires_at: int) -> str:
        """Create a local first-party session."""

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return a session with its user profile when active."""

    def delete_session(self, session_id: str) -> None:
        """Delete a local first-party session."""


class OAuthTransport:
    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
        data = urlencode(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method="POST")
        with urlopen(request, timeout=12) as result:
            return json.loads(result.read().decode("utf-8"))

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any] | list[dict[str, Any]]:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=12) as result:
            return json.loads(result.read().decode("utf-8"))


class InMemoryAuthStore:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}

    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        stored = dict(user)
        self.users[stored["userId"]] = stored
        return dict(stored)

    def create_session(self, user_id: str, expires_at: int) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {"sessionId": session_id, "userId": user_id, "expiresAt": expires_at}
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session or session["expiresAt"] <= int(time.time()):
            return None

        user = self.users.get(session["userId"])
        return {**session, "user": dict(user)} if user else None

    def delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)


class AuthService:
    def __init__(
        self,
        store: AuthStore | None = None,
        settings: dict[str, Any] | None = None,
        transport: OAuthTransport | None = None,
    ) -> None:
        self.store = store or InMemoryAuthStore()
        self.settings = settings or settings_from_env()
        self.transport = transport or OAuthTransport()

    def providers(self, trace_id: str) -> dict[str, Any]:
        data = [
            {
                "provider": provider,
                "label": "Google" if provider == "google" else "GitHub",
                "configured": self._provider_ready(provider),
                "loginUrl": f"/api/auth/login/{provider}",
            }
            for provider in PROVIDERS
        ]
        return response(200, envelope(data, trace_id), trace_id)

    def start_login(self, provider: str, trace_id: str, path: str, return_to: str | None = None) -> dict[str, Any]:
        if provider not in PROVIDERS:
            return self._auth_problem(404, "Unknown auth provider", path, trace_id)

        if not self._provider_ready(provider):
            return self._auth_problem(503, "Auth provider is not configured.", path, trace_id)

        state = secrets.token_urlsafe(24)
        verifier = secrets.token_urlsafe(48)
        transaction = {
            "provider": provider,
            "state": state,
            "verifier": verifier,
            "exp": int(time.time()) + TX_TTL_SECONDS,
        }
        safe_return_to = _safe_return_to(return_to)
        if safe_return_to:
            transaction["returnTo"] = safe_return_to
        location = self._authorization_url(provider, state, verifier)
        cookie = self._cookie(AUTH_TX_COOKIE, sign(transaction, self._secret()), max_age=TX_TTL_SECONDS)
        return redirect(location, trace_id, [cookie])

    def complete_callback(self, provider: str, query: dict[str, list[str]], headers: dict[str, str], trace_id: str) -> dict[str, Any]:
        failure_cookies = [self._clear_cookie(AUTH_TX_COOKIE)]
        if provider not in PROVIDERS:
            return redirect(self._return_url("failed", "unknown_provider"), trace_id, failure_cookies)

        if query.get("error"):
            return redirect(self._return_url("failed", "provider_denied"), trace_id, failure_cookies)

        code = first(query, "code")
        state = first(query, "state")
        transaction = self._read_transaction(headers.get("Cookie", ""))

        if not code or not state or not transaction or transaction.get("provider") != provider or transaction.get("state") != state:
            return redirect(self._return_url("failed", "state", _transaction_return_to(transaction)), trace_id, failure_cookies)

        try:
            profile = self._google_profile(code) if provider == "google" else self._github_profile(code, transaction["verifier"])
        except Exception:
            return redirect(self._return_url("failed", "provider_exchange", _transaction_return_to(transaction)), trace_id, failure_cookies)

        user = self.store.upsert_user(profile)
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        session_id = self.store.create_session(user["userId"], expires_at)
        cookies = [
            self._clear_cookie(AUTH_TX_COOKIE),
            self._cookie(SESSION_COOKIE, session_id, max_age=SESSION_TTL_SECONDS),
        ]
        return redirect(self._return_url("success", None, _transaction_return_to(transaction)), trace_id, cookies)

    def session(self, headers: dict[str, str], trace_id: str) -> dict[str, Any]:
        payload = self.session_payload(headers)
        return response(200, envelope(payload, trace_id), trace_id)

    def session_payload(self, headers: dict[str, str]) -> dict[str, Any]:
        session_id = cookie_value(headers.get("Cookie", ""), SESSION_COOKIE)
        if not session_id:
            return anonymous_session()

        session = self.store.get_session(session_id)
        if not session:
            return anonymous_session()

        return {
            "authenticated": True,
            "user": session["user"],
            "expiresAt": epoch_to_iso(session["expiresAt"]),
        }

    def logout(self, headers: dict[str, str], trace_id: str) -> dict[str, Any]:
        session_id = cookie_value(headers.get("Cookie", ""), SESSION_COOKIE)
        if session_id:
            self.store.delete_session(session_id)

        result = response(200, envelope(anonymous_session(), trace_id), trace_id)
        result["headers"]["Set-Cookie"] = [self._clear_cookie(SESSION_COOKIE)]
        return result

    def require_session(self, headers: dict[str, str], trace_id: str, path: str) -> dict[str, Any] | None:
        if not self.settings["auth_required"]:
            return None

        if self.session_payload(headers)["authenticated"]:
            return None

        return response(
            401,
            problem(
                status=401,
                title="Authentication required",
                detail="Sign in before using this prelaunch API route.",
                instance=path,
                trace_id=trace_id,
                code="auth-required",
            ),
            trace_id,
            content_type="application/problem+json",
        )

    def _provider_ready(self, provider: str) -> bool:
        credentials = self.settings["providers"].get(provider) or {}
        return bool(credentials.get("client_id") and credentials.get("client_secret") and self._secret())

    def _authorization_url(self, provider: str, state: str, verifier: str) -> str:
        redirect_uri = self._callback_url(provider)
        credentials = self.settings["providers"][provider]

        if provider == "google":
            params = {
                "client_id": credentials["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
            return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        params = {
            "client_id": credentials["client_id"],
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    def _google_profile(self, code: str) -> dict[str, Any]:
        credentials = self.settings["providers"]["google"]
        token = self.transport.post_form("https://oauth2.googleapis.com/token", {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._callback_url("google"),
        }, {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        access_token = token.get("access_token")
        if not access_token:
            raise ValueError("missing Google access token")

        userinfo = self.transport.get_json("https://openidconnect.googleapis.com/v1/userinfo", {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        })
        if not isinstance(userinfo, dict) or not userinfo.get("sub"):
            raise ValueError("missing Google userinfo")

        claims = decode_jwt_payload(str(token.get("id_token") or ""))
        validate_google_claims(claims, credentials["client_id"])
        if str(claims["sub"]) != str(userinfo["sub"]):
            raise ValueError("Google subject mismatch")
        return profile("google", str(userinfo["sub"]), userinfo.get("name"), userinfo.get("email"), userinfo.get("picture"))

    def _github_profile(self, code: str, verifier: str) -> dict[str, Any]:
        credentials = self.settings["providers"]["github"]
        token = self.transport.post_form("https://github.com/login/oauth/access_token", {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "code": code,
            "redirect_uri": self._callback_url("github"),
            "code_verifier": verifier,
        }, {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        access_token = token.get("access_token")
        if not access_token:
            raise ValueError("missing GitHub access token")

        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {access_token}"}
        user = self.transport.get_json("https://api.github.com/user", headers)
        if not isinstance(user, dict) or "id" not in user:
            raise ValueError("missing GitHub user")

        email = user.get("email") or self._github_primary_email(headers)
        return profile("github", str(user["id"]), user.get("name") or user.get("login"), email, user.get("avatar_url"))

    def _github_primary_email(self, headers: dict[str, str]) -> str | None:
        emails = self.transport.get_json("https://api.github.com/user/emails", headers)
        if not isinstance(emails, list):
            return None

        for item in emails:
            if item.get("primary") and item.get("verified") and item.get("email"):
                return str(item["email"])

        return None

    def _callback_url(self, provider: str) -> str:
        return f"{self.settings['redirect_base_url'].rstrip('/')}/api/auth/callback/{provider}"

    def _return_url(self, status: str, reason: str | None, return_to: str | None = None) -> str:
        target = self._frontend_return_url(return_to)
        parsed = urlparse(target)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        params["auth"] = status
        if reason:
            params["reason"] = reason
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(params), parsed.fragment))

    def _frontend_return_url(self, return_to: str | None) -> str:
        fallback = str(self.settings["frontend_return_url"])
        safe_return_to = _safe_return_to(return_to)
        if not safe_return_to:
            return fallback

        parsed_fallback = urlparse(fallback)
        if not parsed_fallback.scheme or not parsed_fallback.netloc:
            return fallback

        parsed_return = urlparse(safe_return_to)
        return urlunparse((
            parsed_fallback.scheme,
            parsed_fallback.netloc,
            parsed_return.path or "/",
            "",
            parsed_return.query,
            parsed_return.fragment,
        ))

    def _read_transaction(self, cookie_header: str) -> dict[str, Any] | None:
        value = cookie_value(cookie_header, AUTH_TX_COOKIE)
        if not value:
            return None
        return unsign(value, self._secret())

    def _cookie(self, name: str, value: str, max_age: int) -> str:
        cookie = f"{name}={value}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Lax"
        return f"{cookie}; Secure" if self.settings["cookie_secure"] else cookie

    def _clear_cookie(self, name: str) -> str:
        cookie = f"{name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        return f"{cookie}; Secure" if self.settings["cookie_secure"] else cookie

    def _secret(self) -> str:
        return str(self.settings["session_secret"] or "")

    def _auth_problem(self, status: int, detail: str, path: str, trace_id: str) -> dict[str, Any]:
        return response(
            status,
            problem(status=status, title="Authentication unavailable", detail=detail, instance=path, trace_id=trace_id, code="auth-unavailable"),
            trace_id,
            content_type="application/problem+json",
        )


def settings_from_env() -> dict[str, Any]:
    return {
        "auth_required": env_bool("LAWDIT_AUTH_REQUIRED", False),
        "cookie_secure": env_bool("LAWDIT_COOKIE_SECURE", False),
        "frontend_return_url": os.environ.get("LAWDIT_FRONTEND_RETURN_URL", "http://localhost:5173/dashboard"),
        "redirect_base_url": os.environ.get("LAWDIT_AUTH_REDIRECT_BASE_URL", "http://localhost:8000"),
        "session_secret": os.environ.get("LAWDIT_SESSION_SECRET", ""),
        "providers": {
            "google": {"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "")},
            "github": {"client_id": os.environ.get("GITHUB_CLIENT_ID", ""), "client_secret": os.environ.get("GITHUB_CLIENT_SECRET", "")},
        },
    }


def _safe_return_to(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    if len(candidate) > 512 or any(character in candidate for character in ("\r", "\n")):
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or candidate.startswith("//"):
        return None
    if not parsed.path.startswith("/"):
        return None
    if parsed.path == "/api" or parsed.path.startswith("/api/"):
        return None
    return urlunparse(("", "", parsed.path, "", parsed.query, parsed.fragment))


def _transaction_return_to(transaction: dict[str, Any] | None) -> str | None:
    return str(transaction.get("returnTo")) if isinstance(transaction, dict) and isinstance(transaction.get("returnTo"), str) else None
