"""Small helpers for the prelaunch auth boundary."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from http.cookies import SimpleCookie
from typing import Any

CONTRACT_VERSION = "0.1.0"


def anonymous_session() -> dict[str, Any]:
    return {"authenticated": False, "user": None, "expiresAt": None}


def cookie_value(cookie_header: str, name: str) -> str | None:
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    return cookie[name].value if name in cookie else None


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("invalid JWT")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))


def validate_google_claims(claims: dict[str, Any], client_id: str) -> None:
    if claims.get("aud") != client_id:
        raise ValueError("invalid audience")
    if claims.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise ValueError("invalid issuer")
    if int(claims.get("exp") or 0) <= int(time.time()):
        raise ValueError("expired ID token")
    if not claims.get("sub"):
        raise ValueError("missing subject")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def epoch_to_iso(epoch: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values else None


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def profile(provider: str, subject: str, name: Any, email: Any, avatar: Any) -> dict[str, Any]:
    user_id = "user_" + hashlib.sha256(f"{provider}:{subject}".encode("utf-8")).hexdigest()[:16]
    return {
        "userId": user_id,
        "provider": provider,
        "providerSubject": subject,
        "displayName": str(name or email or f"{provider} user"),
        "email": str(email) if email else None,
        "avatarUrl": str(avatar) if avatar else None,
    }


def redirect(location: str, trace_id: str, cookies: list[str]) -> dict[str, Any]:
    return {
        "status": 302,
        "contentType": "application/json",
        "headers": {"Location": location, "Set-Cookie": cookies, "X-Trace-Id": trace_id, "X-Contract-Version": CONTRACT_VERSION},
        "body": {},
    }


def sign(payload: dict[str, Any], secret: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def unsign(value: str, secret: str) -> dict[str, Any] | None:
    try:
        encoded, signature = value.rsplit(".", 1)
    except ValueError:
        return None

    expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None

    payload = encoded + "=" * (-len(encoded) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))
    return data if int(data.get("exp") or 0) > int(time.time()) else None
