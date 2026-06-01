from __future__ import annotations

import http.client
import json
from pathlib import Path
import threading
import time
import unittest
from unittest import mock
from http.server import ThreadingHTTPServer
from tempfile import TemporaryDirectory

from backend.lawdit.auth import AUTH_TX_COOKIE, SESSION_COOKIE, AuthService, InMemoryAuthStore
from backend.lawdit.auth_support import cookie_value, unsign
from backend.lawdit import build_default_app, make_handler
from backend.lawdit.google_drive_binding import DRIVE_BIND_TX_COOKIE, GoogleDriveBindingService
from backend.lawdit.public_analysis import MAX_UPLOAD_BYTES, PublicAnalysisService
from backend.lawdit.public_analysis_capacity import PublicAnalysisCapacity
from backend.lawdit.source_http import SourceHttpApp, SourceHttpOptions, build_sqlite_app
from backend.lawdit.source_documents import SourceDocument, SourceDocumentBatch
from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.persistent_demo_state import PersistentPrelaunchState
from backend.lawdit.sqlite_store import SQLiteAuthStore, SQLiteDocumentStore, SQLiteDriveBindingStore
from backend.lawdit.source_store import SourceStore


class FakeOAuthTransport:
    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, str]:
        self.last_post = {"url": url, "payload": payload, "headers": headers}
        return {"access_token": "provider_token_not_returned", "token_type": "bearer"}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, object] | list[dict[str, object]]:
        self.last_get = {"url": url, "headers": headers}
        if url.endswith("/user/emails"):
            return [{"email": "privacy.reviewer@example.org", "primary": True, "verified": True}]
        return {"id": 42, "login": "privacy-reviewer", "name": "Privacy Reviewer", "email": None, "avatar_url": "https://avatars.example/reviewer.png"}


class FakeDriveBindingTransport:
    def __init__(self) -> None:
        self.refresh_count = 0
        self.revoked_tokens: list[str] = []

    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, str]:
        if payload.get("grant_type") == "authorization_code":
            return {
                "access_token": "drive_callback_access_not_returned",
                "refresh_token": "drive_refresh_not_returned",
                "scope": "openid email profile https://www.googleapis.com/auth/drive.readonly",
                "token_type": "Bearer",
            }
        if payload.get("grant_type") == "refresh_token":
            self.refresh_count += 1
            return {"access_token": "drive_refreshed_access", "token_type": "Bearer"}
        return {}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, object]:
        return {
            "sub": "google-drive-subject",
            "name": "Drive Reviewer",
            "email": "drive.reviewer@example.org",
            "picture": "https://photos.example/drive-reviewer.png",
        }

    def revoke_token(self, token: str) -> bool:
        self.revoked_tokens.append(token)
        return True


def auth_settings(auth_required: bool = False) -> dict[str, object]:
    return {
        "auth_required": auth_required,
        "cookie_secure": False,
        "frontend_return_url": "http://localhost:5173/dashboard",
        "redirect_base_url": "http://localhost:8000",
        "session_secret": "test-session-secret",
        "providers": {
            "google": {"client_id": "google-client", "client_secret": "google-secret"},
            "github": {"client_id": "github-client", "client_secret": "github-secret"},
        },
    }


def auth_app(auth_required: bool = False) -> SourceHttpApp:
    service = AuthService(InMemoryAuthStore(), auth_settings(auth_required), FakeOAuthTransport())
    return SourceHttpApp(auth_service=service)


def start_github_session(app: SourceHttpApp) -> str:
    login = app.handle("GET", "/api/auth/login/github", "trace_auth_login")
    auth_cookie = login["headers"]["Set-Cookie"][0]
    tx_value = cookie_value(auth_cookie, AUTH_TX_COOKIE)
    assert tx_value is not None
    tx = unsign(tx_value, "test-session-secret")
    assert tx is not None
    callback = app.handle(
        "GET",
        f"/api/auth/callback/github?code=oauth_code&state={tx['state']}",
        "trace_auth_callback",
        None,
        None,
        {"Cookie": auth_cookie},
    )
    session_cookies = [item for item in callback["headers"]["Set-Cookie"] if item.startswith(f"{SESSION_COOKIE}=")]
    assert session_cookies
    return session_cookies[0]


class MemoryWorkflowStore:
    def __init__(self, snapshot: dict[str, object]) -> None:
        self.snapshot = snapshot
        self.saved: dict[str, object] | None = None

    def load(self) -> dict[str, object]:
        return self.snapshot

    def save(self, payload: dict[str, object]) -> None:
        self.saved = payload


def create_sqlite_session(db_path: Path, user_id: str, subject: str) -> str:
    store = SQLiteAuthStore(SQLiteDocumentStore(db_path))
    store.upsert_user({
        "userId": user_id,
        "provider": "github",
        "providerSubject": subject,
        "displayName": subject,
        "email": f"{subject}@example.invalid",
        "avatarUrl": None,
    })
    session_id = store.create_session(user_id, int(time.time()) + 600)
    return f"{SESSION_COOKIE}={session_id}"


def multipart_file(filename: str, content: bytes, content_type: str = "text/plain") -> tuple[bytes, str]:
    boundary = "----lawdit-test-boundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n"
        "\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


class BackendApiServerTests(unittest.TestCase):
    def test_health_and_sources_use_contract_envelopes(self) -> None:
        app = build_default_app()

        health = app.handle("GET", "/api/health", "trace_test_health")
        sources = app.handle("GET", "/api/sources", "trace_test_sources")

        self.assertEqual(health["status"], 200)
        self.assertTrue(health["body"]["data"]["ok"])
        self.assertEqual(health["headers"]["X-Contract-Version"], "0.1.0")
        self.assertEqual(sources["status"], 200)
        self.assertGreaterEqual(len(sources["body"]["data"]), 1)
        self.assertEqual(sources["body"]["meta"]["contractVersion"], "0.1.0")

    def test_public_analysis_capacity_is_public_and_bounded(self) -> None:
        app = build_default_app()

        capacity = app.handle("GET", "/api/public-analysis/capacity", "trace_public_capacity")

        self.assertEqual(capacity["status"], 200)
        self.assertEqual(capacity["body"]["data"]["maxActive"], 10)
        self.assertEqual(capacity["body"]["data"]["activeAnalyses"], 0)
        self.assertEqual(capacity["body"]["data"]["fileSizeLimitBytes"], MAX_UPLOAD_BYTES)

    def test_public_analysis_upload_returns_redacted_summary(self) -> None:
        app = build_default_app()
        body, content_type = multipart_file(
            "employee-note.txt",
            b"Employee email: privacy.reviewer@example.org\nSSN: 123-45-6789\n",
        )

        analyzed = app.handle(
            "POST",
            "/api/public-analysis/analyze",
            "trace_public_analyze",
            body,
            content_type,
            {"X-Lawdit-Trial-Session": "trial-session-a"},
        )
        serialized = json.dumps(analyzed["body"])

        self.assertEqual(analyzed["status"], 200)
        self.assertEqual(analyzed["body"]["data"]["status"], "completed")
        self.assertEqual(analyzed["body"]["data"]["summary"]["riskLevel"], "high")
        self.assertGreaterEqual(analyzed["body"]["data"]["summary"]["detectedSignalCount"], 2)
        self.assertIn("nextSteps", analyzed["body"]["data"]["summary"])
        self.assertIn("analysisStages", analyzed["body"]["data"])
        self.assertIn("governanceBoundaries", analyzed["body"]["data"])
        self.assertIn("[REDACTED", serialized)
        self.assertNotIn("privacy.reviewer@example.org", serialized)
        self.assertNotIn("123-45-6789", serialized)

    def test_public_analysis_rejects_oversized_file_before_analysis(self) -> None:
        app = build_default_app()
        body, content_type = multipart_file("large.txt", b"x" * (MAX_UPLOAD_BYTES + 1))

        rejected = app.handle(
            "POST",
            "/api/public-analysis/analyze",
            "trace_public_large",
            body,
            content_type,
            {"X-Lawdit-Trial-Session": "trial-session-large"},
        )

        self.assertEqual(rejected["status"], 413)
        self.assertEqual(rejected["contentType"], "application/problem+json")
        self.assertEqual(rejected["body"]["capacity"]["activeAnalyses"], 0)

    def test_public_analysis_rejects_second_active_file_for_session(self) -> None:
        capacity = PublicAnalysisCapacity(max_active=1)
        reservation, _status, error = capacity.try_begin("trial-session-a")
        self.assertIsNone(error)
        assert reservation is not None
        app = SourceHttpApp(options=SourceHttpOptions(public_analysis=PublicAnalysisService(capacity)))
        body, content_type = multipart_file("second.txt", b"Email: privacy@example.org")

        rejected = app.handle(
            "POST",
            "/api/public-analysis/analyze",
            "trace_public_duplicate",
            body,
            content_type,
            {"X-Lawdit-Trial-Session": "trial-session-a"},
        )

        capacity.finish(reservation)
        self.assertEqual(rejected["status"], 409)
        self.assertTrue(rejected["body"]["capacity"]["userHasActiveAnalysis"])

    def test_public_analysis_reports_waiting_users_when_capacity_is_full(self) -> None:
        capacity = PublicAnalysisCapacity(max_active=1)
        reservation, _status, error = capacity.try_begin("trial-session-a")
        self.assertIsNone(error)
        assert reservation is not None
        app = SourceHttpApp(options=SourceHttpOptions(public_analysis=PublicAnalysisService(capacity)))
        body, content_type = multipart_file("queued.txt", b"Email: waiting@example.org")

        rejected = app.handle(
            "POST",
            "/api/public-analysis/analyze",
            "trace_public_full",
            body,
            content_type,
            {"X-Lawdit-Trial-Session": "trial-session-b"},
        )

        capacity.finish(reservation)
        self.assertEqual(rejected["status"], 429)
        self.assertEqual(rejected["body"]["capacity"]["waitingUsers"], 1)
        self.assertEqual(rejected["body"]["capacity"]["userQueuePosition"], 1)

    def test_auth_provider_list_does_not_expose_secrets(self) -> None:
        app = auth_app()

        providers = app.handle("GET", "/api/auth/providers", "trace_auth_providers")
        serialized = json.dumps(providers["body"])

        self.assertEqual(providers["status"], 200)
        self.assertEqual({item["provider"] for item in providers["body"]["data"]}, {"google", "github"})
        self.assertTrue(all(item["configured"] for item in providers["body"]["data"]))
        self.assertNotIn("google-secret", serialized)
        self.assertNotIn("github-secret", serialized)

    def test_unconfigured_provider_rejects_login_without_session(self) -> None:
        settings = auth_settings()
        settings["providers"] = {"google": {"client_id": "", "client_secret": ""}, "github": {"client_id": "", "client_secret": ""}}
        app = SourceHttpApp(auth_service=AuthService(InMemoryAuthStore(), settings, FakeOAuthTransport()))

        rejected = app.handle("GET", "/api/auth/login/github", "trace_auth_unconfigured")

        self.assertEqual(rejected["status"], 503)
        self.assertEqual(rejected["contentType"], "application/problem+json")

    def test_github_callback_state_mismatch_does_not_create_session(self) -> None:
        app = auth_app()
        login = app.handle("GET", "/api/auth/login/github", "trace_auth_login")
        callback = app.handle(
            "GET",
            "/api/auth/callback/github?code=oauth_code&state=wrong",
            "trace_auth_bad_state",
            None,
            None,
            {"Cookie": login["headers"]["Set-Cookie"][0]},
        )
        session = app.handle("GET", "/api/auth/session", "trace_auth_session")

        self.assertEqual(callback["status"], 302)
        self.assertIn("auth=failed", callback["headers"]["Location"])
        self.assertFalse(session["body"]["data"]["authenticated"])

    def test_auth_callback_returns_to_safe_deep_link_after_login(self) -> None:
        app = auth_app()
        login = app.handle("GET", "/api/auth/login/github?returnTo=/findings/finding_001%3Ftab%3Devidence", "trace_auth_login")
        auth_cookie = login["headers"]["Set-Cookie"][0]
        tx_value = cookie_value(auth_cookie, AUTH_TX_COOKIE)
        transaction = unsign(str(tx_value or ""), str(app.auth_service.settings["session_secret"]))
        callback = app.handle(
            "GET",
            f"/api/auth/callback/github?code=oauth_code&state={transaction['state']}",
            "trace_auth_callback",
            None,
            None,
            {"Cookie": f"{AUTH_TX_COOKIE}={tx_value}"},
        )

        self.assertEqual(transaction["returnTo"], "/findings/finding_001?tab=evidence")
        self.assertEqual(callback["status"], 302)
        self.assertEqual(callback["headers"]["Location"], "http://localhost:5173/findings/finding_001?tab=evidence&auth=success")

    def test_auth_login_ignores_external_return_targets(self) -> None:
        app = auth_app()
        login = app.handle("GET", "/api/auth/login/github?returnTo=https%3A%2F%2Fevil.example%2Ffindings", "trace_auth_login")
        auth_cookie = login["headers"]["Set-Cookie"][0]
        tx_value = cookie_value(auth_cookie, AUTH_TX_COOKIE)
        transaction = unsign(str(tx_value or ""), str(app.auth_service.settings["session_secret"]))
        callback = app.handle(
            "GET",
            f"/api/auth/callback/github?code=oauth_code&state={transaction['state']}",
            "trace_auth_callback",
            None,
            None,
            {"Cookie": f"{AUTH_TX_COOKIE}={tx_value}"},
        )

        self.assertNotIn("returnTo", transaction)
        self.assertEqual(callback["status"], 302)
        self.assertEqual(callback["headers"]["Location"], "http://localhost:5173/dashboard?auth=success")

        api_login = app.handle("GET", "/api/auth/login/github?returnTo=/api", "trace_auth_login")
        api_cookie = api_login["headers"]["Set-Cookie"][0]
        api_tx_value = cookie_value(api_cookie, AUTH_TX_COOKIE)
        api_transaction = unsign(str(api_tx_value or ""), str(app.auth_service.settings["session_secret"]))
        self.assertNotIn("returnTo", api_transaction)

    def test_github_callback_creates_safe_session_and_logout_revokes_it(self) -> None:
        app = auth_app()
        session_cookie = start_github_session(app)
        session = app.handle("GET", "/api/auth/session", "trace_auth_session", None, None, {"Cookie": session_cookie})
        serialized = json.dumps(session["body"])

        self.assertTrue(session["body"]["data"]["authenticated"])
        self.assertEqual(session["body"]["data"]["user"]["provider"], "github")
        self.assertEqual(session["body"]["data"]["user"]["email"], "privacy.reviewer@example.org")
        self.assertNotIn("provider_token_not_returned", serialized)

        logged_out = app.handle("POST", "/api/auth/logout", "trace_auth_logout", "{}", "application/json", {"Cookie": session_cookie})
        after_logout = app.handle("GET", "/api/auth/session", "trace_auth_after_logout", None, None, {"Cookie": session_cookie})

        self.assertFalse(logged_out["body"]["data"]["authenticated"])
        self.assertFalse(after_logout["body"]["data"]["authenticated"])

    def test_google_drive_binding_connect_status_and_disconnect_do_not_expose_tokens(self) -> None:
        auth_service = AuthService(InMemoryAuthStore(), auth_settings(), FakeOAuthTransport())
        drive_transport = FakeDriveBindingTransport()
        drive_service = GoogleDriveBindingService(settings=auth_service.settings, transport=drive_transport)
        app = SourceHttpApp(auth_service=auth_service, drive_binding_service=drive_service)
        session_cookie = start_github_session(app)

        start = app.handle("GET", "/api/integrations/google-drive/bind/start", "trace_drive_bind_start", None, None, {"Cookie": session_cookie})
        tx_cookie = start["headers"]["Set-Cookie"][0]
        tx_value = cookie_value(tx_cookie, DRIVE_BIND_TX_COOKIE)
        assert tx_value is not None
        tx = unsign(tx_value, "test-session-secret")
        assert tx is not None
        callback = app.handle(
            "GET",
            f"/api/integrations/google-drive/bind/callback?code=drive_code&state={tx['state']}",
            "trace_drive_bind_callback",
            None,
            None,
            {"Cookie": f"{session_cookie}; {DRIVE_BIND_TX_COOKIE}={tx_value}"},
        )
        status = app.handle("GET", "/api/integrations/google-drive/binding", "trace_drive_bind_status", None, None, {"Cookie": session_cookie})
        serialized = json.dumps(status["body"])
        disconnected = app.handle("DELETE", "/api/integrations/google-drive/binding", "trace_drive_bind_disconnect", None, None, {"Cookie": session_cookie})

        self.assertEqual(start["status"], 302)
        self.assertIn("access_type=offline", start["headers"]["Location"])
        self.assertIn("drive.readonly", start["headers"]["Location"])
        self.assertEqual(callback["status"], 302)
        self.assertIn("driveBinding=success", callback["headers"]["Location"])
        self.assertTrue(status["body"]["data"]["connected"])
        self.assertEqual(status["body"]["data"]["email"], "drive.reviewer@example.org")
        self.assertNotIn("drive_refresh_not_returned", serialized)
        self.assertNotIn("drive_callback_access_not_returned", serialized)
        self.assertFalse(disconnected["body"]["data"]["connected"])
        self.assertEqual(drive_transport.revoked_tokens, ["drive_refresh_not_returned"])

    def test_auth_required_protects_workflow_routes(self) -> None:
        app = auth_app(auth_required=True)

        rejected = app.handle("GET", "/api/sources", "trace_auth_required")
        session_cookie = start_github_session(app)
        accepted = app.handle("GET", "/api/sources", "trace_auth_sources", None, None, {"Cookie": session_cookie})

        self.assertEqual(rejected["status"], 401)
        self.assertEqual(rejected["contentType"], "application/problem+json")
        self.assertEqual(accepted["status"], 200)

    def test_sqlite_auth_required_sources_are_scoped_to_session_user(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            cookie_a = create_sqlite_session(db_path, "user_account_a", "account-a")
            cookie_b = create_sqlite_session(db_path, "user_account_b", "account-b")
            with mock.patch.dict("os.environ", {"LAWDIT_AUTH_REQUIRED": "true", "LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_account_a_create",
                    json.dumps({
                        "sourceId": "source_account_a_only",
                        "name": "Account A Source",
                        "sourceType": "remote_file_link",
                        "rootLabel": "https://example.com/account-a.txt",
                        "config": {"url": "https://example.com/account-a.txt"},
                    }),
                    "application/json",
                    {"Cookie": cookie_a},
                )
                list_a = app.handle("GET", "/api/sources", "trace_account_a_sources", None, None, {"Cookie": cookie_a})
                list_b = app.handle("GET", "/api/sources", "trace_account_b_sources", None, None, {"Cookie": cookie_b})
                delete_b = app.handle("DELETE", "/api/sources/source_account_a_only", "trace_account_b_delete", None, None, {"Cookie": cookie_b})

        self.assertEqual(created["status"], 201)
        self.assertIn("source_account_a_only", {source["sourceId"] for source in list_a["body"]["data"]})
        self.assertNotIn("source_account_a_only", {source["sourceId"] for source in list_b["body"]["data"]})
        self.assertEqual(delete_b["status"], 404)

    def test_sqlite_auth_required_findings_are_scoped_to_session_user(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "account-a.txt").write_text("Contact privacy.user@example.org for ticket 491711234567.", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"
            cookie_a = create_sqlite_session(db_path, "user_findings_a", "findings-a")
            cookie_b = create_sqlite_session(db_path, "user_findings_b", "findings-b")
            with mock.patch.dict("os.environ", {"LAWDIT_AUTH_REQUIRED": "true", "LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_findings_a_create",
                    json.dumps({
                        "sourceId": "source_findings_a_only",
                        "name": "Account A Local",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                    {"Cookie": cookie_a},
                )
                connected = app.handle("POST", "/api/sources/source_findings_a_only/connect-test", "trace_findings_a_connect", "{}", "application/json", {"Cookie": cookie_a})
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_findings_a_scan",
                    json.dumps({"sourceId": "source_findings_a_only"}),
                    "application/json",
                    {"Cookie": cookie_a},
                )
                time.sleep(1.1)
                findings_a = app.handle("GET", "/api/findings", "trace_findings_a_list", None, None, {"Cookie": cookie_a})
                findings_b = app.handle("GET", "/api/findings", "trace_findings_b_list", None, None, {"Cookie": cookie_b})
                finding_id = findings_a["body"]["data"][0]["findingId"]
                detail_b = app.handle("GET", f"/api/findings/{finding_id}", "trace_findings_b_detail", None, None, {"Cookie": cookie_b})

        self.assertEqual(created["status"], 201)
        self.assertEqual(connected["body"]["data"]["connectionStatus"], "connected")
        self.assertEqual(started["status"], 202)
        self.assertEqual(len(findings_a["body"]["data"]), 1)
        self.assertEqual(findings_b["body"]["data"], [])
        self.assertEqual(detail_b["status"], 404)

    def test_auth_required_protects_google_drive_picker_config(self) -> None:
        app = auth_app(auth_required=True)

        with mock.patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-secret-not-public",
            "GOOGLE_PICKER_API_KEY": "picker-public-key",
            "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
        }):
            rejected = app.handle("GET", "/api/integrations/google-drive/picker-config", "trace_picker_rejected")
            session_cookie = start_github_session(app)
            accepted = app.handle(
                "GET",
                "/api/integrations/google-drive/picker-config",
                "trace_picker_accepted",
                None,
                None,
                {"Cookie": session_cookie},
            )
            serialized = json.dumps(accepted["body"])

        self.assertEqual(rejected["status"], 401)
        self.assertEqual(rejected["contentType"], "application/problem+json")
        self.assertEqual(accepted["status"], 200)
        self.assertTrue(accepted["body"]["data"]["configured"])
        self.assertNotIn("google-secret-not-public", serialized)

    def test_scan_start_rejects_not_ready_source_without_state_change(self) -> None:
        app = build_default_app()
        before = app.handle("GET", "/api/audit/events", "trace_test_audit_before")

        rejected = app.handle(
            "POST",
            "/api/scans/full",
            "trace_test_scan_rejected",
            json.dumps({"sourceId": "source_002"}),
            "application/json",
        )
        after = app.handle("GET", "/api/audit/events", "trace_test_audit_after")

        self.assertEqual(rejected["status"], 409)
        self.assertEqual(rejected["contentType"], "application/problem+json")
        self.assertEqual(len(after["body"]["data"]), len(before["body"]["data"]))

    def test_sqlite_source_store_persists_created_sources(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            app = build_sqlite_app(db_path)
            created = app.handle(
                "POST",
                "/api/sources",
                "trace_test_create_source",
                json.dumps({
                    "sourceId": "source_sqlite_local",
                    "name": "SQLite Local Source",
                    "sourceType": "local_repo",
                    "status": "registered",
                    "config": {"rootPath": "/tmp/lawdit-sample"},
                }),
                "application/json",
            )

            restarted = build_sqlite_app(db_path)
            sources = restarted.handle("GET", "/api/sources", "trace_test_sources_restart")
            source_ids = {source["sourceId"] for source in sources["body"]["data"]}

            self.assertEqual(created["status"], 201)
            self.assertIn("source_sqlite_local", source_ids)

    def test_sqlite_workflow_state_persists_review_after_restart(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            app = build_sqlite_app(db_path)
            support = app.handle("GET", "/api/findings/finding_001/review-support", "trace_sqlite_support")
            checklist_ids = [item["itemId"] for item in support["body"]["data"]["checklist"]]
            reviewed = app.handle(
                "POST",
                "/api/findings/finding_001/review",
                "trace_sqlite_review",
                json.dumps({
                    "actorId": "user_anna",
                    "checklistItemIds": checklist_ids,
                    "decision": "escalate",
                    "nextAction": "legal_escalation",
                    "reason": "Needs DPO review before any retention action.",
                }),
                "application/json",
            )

            restarted = build_sqlite_app(db_path)
            finding = restarted.handle("GET", "/api/findings/finding_001", "trace_sqlite_finding")
            audit_events = restarted.handle("GET", "/api/audit/events", "trace_sqlite_audit")

            self.assertEqual(reviewed["status"], 201)
            self.assertEqual(finding["body"]["data"]["status"], "escalated")
            self.assertEqual(audit_events["body"]["data"][0]["eventType"], "review_recorded")

    def test_prelaunch_mode_clears_historical_sqlite_demo_rows_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "placeholder.txt").write_text("placeholder", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"
            seeded = build_sqlite_app(db_path)
            created = seeded.handle(
                "POST",
                "/api/sources",
                "trace_seed_real_source",
                json.dumps({
                    "sourceId": "source_real_local",
                    "name": "Real Local Source",
                    "sourceType": "local_repo",
                    "status": "registered",
                    "rootLabel": str(root),
                    "masterOfDataUserId": "owner_real",
                    "config": {"rootPath": str(root)},
                }),
                "application/json",
            )
            seeded_findings = seeded.handle("GET", "/api/findings", "trace_seed_findings")

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                prelaunch = build_sqlite_app(db_path, [root])
                sources = prelaunch.handle("GET", "/api/sources", "trace_prelaunch_sources")
                findings = prelaunch.handle("GET", "/api/findings", "trace_prelaunch_findings")
                audit_events = prelaunch.handle("GET", "/api/audit/events", "trace_prelaunch_audit")
                metrics = prelaunch.handle("GET", "/api/admin/metrics", "trace_prelaunch_metrics")

            self.assertEqual(created["status"], 201)
            self.assertGreater(len(seeded_findings["body"]["data"]), 0)
            self.assertEqual([source["sourceId"] for source in sources["body"]["data"]], ["source_real_local"])
            self.assertEqual(findings["body"]["data"], [])
            self.assertEqual(audit_events["body"]["data"], [])
            self.assertEqual(metrics["body"]["data"]["flaggedFiles"], 0)

    def test_prelaunch_empty_findings_pagination_uses_real_total(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                findings = app.handle("GET", "/api/findings", "trace_empty_pagination")

        self.assertEqual(findings["body"]["data"], [])
        self.assertEqual(findings["body"]["pagination"]["total"], 0)

    def test_prelaunch_restored_findings_are_sanitized_before_public_response(self) -> None:
        snapshot = {
            "scan": {"scanId": "current", "sourceId": "", "status": "idle", "stage": "not_started", "progress": 0},
            "findings": [{
                "findingId": "finding_old",
                "fileName": "Supplier_Onboarding_Example_A.pdf",
                "sourcePath": "https://drive.google.com/file/d/raw-file-id/view?usp=drivesdk",
                "riskLevel": "medium",
                "riskScore": 64,
                "status": "assigned",
            }],
            "finding_details": {
                "finding_old": {
                    "findingId": "finding_old",
                    "fileName": "Supplier_Onboarding_Example_A.pdf",
                    "sourcePath": "https://drive.google.com/file/d/raw-file-id/view?usp=drivesdk",
                    "riskLevel": "medium",
                    "riskScore": 64,
                    "status": "assigned",
                    "signals": [{
                        "type": "email",
                        "detector": "email_pattern",
                        "confidence": 0.91,
                        "snippet": "Tax ID DE123456789 contact [REDACTED_EMAIL] 12 Vendor Street",
                    }],
                },
            },
        }
        state = PersistentPrelaunchState(SourceStore(), MemoryWorkflowStore(snapshot))
        findings = state.list_findings("trace_restore_findings")
        detail = state.get_finding("finding_old", "trace_restore_detail", "/api/findings/finding_old")
        serialized = json.dumps({"findings": findings["body"], "detail": detail["body"]})

        self.assertEqual(findings["body"]["pagination"]["total"], 1)
        self.assertIn("source_reference:", serialized)
        self.assertIn("Email: [REDACTED_EMAIL]", serialized)
        self.assertNotIn("https://drive.google.com", serialized)
        self.assertNotIn("DE123456789", serialized)
        self.assertNotIn("12 Vendor Street", serialized)

    def test_google_drive_picker_config_exposes_only_public_setup(self) -> None:
        app = auth_app()

        with mock.patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-secret-not-public",
            "GOOGLE_PICKER_API_KEY": "picker-public-key",
            "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
        }):
            config = app.handle("GET", "/api/integrations/google-drive/picker-config", "trace_picker_config")
            serialized = json.dumps(config["body"])

        self.assertEqual(config["status"], 200)
        self.assertTrue(config["body"]["data"]["configured"])
        self.assertEqual(config["body"]["data"]["clientId"], "google-client-id")
        self.assertEqual(config["body"]["data"]["apiKey"], "picker-public-key")
        self.assertNotIn("google-secret-not-public", serialized)

    def test_prelaunch_mode_scans_remote_file_link_without_storing_raw_file(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                self.assertEqual(source["sourceType"], "remote_file_link")
                return SourceDocumentBatch(
                    documents=[SourceDocument("contacts.txt", "https://example.com/contacts.txt", "Contact privacy.reviewer@example.org", 36, "Remote_File")],
                    total_files=1,
                    total_bytes=36,
                    unsupported_files=0,
                    warnings=[],
                    family="Remote_File",
                    extraction_method="remote_https_text",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                with mock.patch("backend.lawdit.source_api.validate_remote_source_url", lambda url: None):
                    created = app.handle(
                        "POST",
                        "/api/sources",
                        "trace_remote_create",
                        json.dumps({
                            "sourceId": "source_remote_file",
                            "name": "Remote contact file",
                            "sourceType": "remote_file_link",
                            "rootLabel": "https://example.com/contacts.txt",
                            "masterOfDataUserId": "owner_remote",
                            "config": {"url": "https://example.com/contacts.txt"},
                        }),
                        "application/json",
                    )
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_remote_scan",
                        json.dumps({"sourceId": "source_remote_file"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    findings = app.handle("GET", "/api/findings", "trace_remote_findings")
                    detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_remote_detail")
                    serialized = json.dumps(detail["body"])

            self.assertEqual(created["status"], 201)
            self.assertEqual(created["body"]["data"]["status"], "connected")
            self.assertEqual(started["status"], 202)
            self.assertEqual(len(findings["body"]["data"]), 1)
            self.assertIn("[REDACTED_EMAIL]", serialized)
            self.assertNotIn("privacy.reviewer@example.org", serialized)

    def test_remote_file_link_rejects_google_drive_share_pages(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                rejected = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_drive_share_rejected",
                    json.dumps({
                        "sourceId": "source_drive_share_link",
                        "name": "Drive share page",
                        "sourceType": "remote_file_link",
                        "rootLabel": "https://drive.google.com/file/d/file-id/view?usp=sharing",
                        "config": {"url": "https://drive.google.com/file/d/file-id/view?usp=sharing"},
                    }),
                    "application/json",
                )

        self.assertEqual(rejected["status"], 422)
        self.assertIn("Google Drive Picker", rejected["body"]["errors"][0]["detail"])

    def test_prelaunch_mode_scans_pdf_text_layer_without_storing_raw_text(self) -> None:
        class FakePdfReader:
            def __init__(self, stream: object, strict: bool = False) -> None:
                self.pages = [mock.Mock(extract_text=lambda: "Passenger support phone +491711234567")]

        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "ticket.pdf").write_bytes(b"%PDF-1.6\nplaceholder")
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_pdf_source_create",
                    json.dumps({
                        "sourceId": "source_pdf_text",
                        "name": "PDF text source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                connected = app.handle("POST", "/api/sources/source_pdf_text/connect-test", "trace_pdf_source_connect", "{}", "application/json")
                with mock.patch("backend.lawdit.source_documents.PdfReader", FakePdfReader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_pdf_scan",
                        json.dumps({"sourceId": "source_pdf_text"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    findings = app.handle("GET", "/api/findings", "trace_pdf_findings")
                    detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_pdf_detail")
                    serialized = json.dumps(detail["body"])

        self.assertEqual(created["status"], 201)
        self.assertEqual(connected["body"]["data"]["connectionStatus"], "connected")
        self.assertEqual(started["status"], 202)
        self.assertEqual(len(findings["body"]["data"]), 1)
        self.assertIn("[REDACTED_PHONE]", serialized)
        self.assertNotIn("+491711234567", serialized)

    def test_prelaunch_signal_detection_covers_form_fields_with_safe_snippets(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "placeholder.txt").write_text("placeholder", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                return SourceDocumentBatch(
                    documents=[
                        SourceDocument("Training_Evaluation_Example_A.pdf", "https://drive.example/training-a", "Participant: Lina Becker\nComments: Follow up on payroll dashboard access.", 100, "Drive"),
                        SourceDocument("IT_Access_Request_Example_A.pdf", "https://drive.example/it-a", "Employee: Marco Klein\nEmployee ID: E-31705\nAccess Level: Admin\nJustification: Needs billing system access.", 100, "Drive"),
                        SourceDocument("Incident_Report_Example_A.pdf", "https://drive.example/incident-a", "Reported By: Sofia Roth\nDescription: Lost badge in reception area.\nCorrective Action: Replace badge.", 100, "Drive"),
                        SourceDocument("Expense_Report_Example_A.pdf", "https://drive.example/expense-a", "Employee Name: Noah Weber\nEmployee ID: E-20491\nAmount: 24.90 EUR", 100, "Drive"),
                        SourceDocument("Supplier_Onboarding_Example_A.pdf", "https://drive.example/supplier-a", "Contact Email: supplier.owner@example.org\nTax ID: DE123456789\nAddress: 12 Vendor Street", 100, "Drive"),
                    ],
                    total_files=5,
                    total_bytes=500,
                    unsupported_files=0,
                    warnings=[],
                    family="Drive",
                    extraction_method="google_drive_text",
                )

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_form_source_create",
                    json.dumps({
                        "sourceId": "source_form_fields",
                        "name": "Form field source",
                        "sourceType": "local_repo",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_form_fields/connect-test", "trace_form_connect")
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_form_scan",
                        json.dumps({"sourceId": "source_form_fields"}),
                        "application/json",
                    )
                    time.sleep(1.1)
                    scan = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_form_scan_done")
                    findings = app.handle("GET", "/api/findings", "trace_form_findings")
                    first_detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_form_detail")
                    serialized = json.dumps({"scan": scan["body"], "detail": first_detail["body"], "findings": findings["body"]})

        signal_types = {item["type"] for item in scan["body"]["data"]["signalDetection"]["signalTypeCounts"]}

        self.assertEqual(len(findings["body"]["data"]), 5)
        self.assertEqual(findings["body"]["pagination"]["total"], 5)
        self.assertTrue({"person_name", "employee_id", "incident_context", "expense_amount", "tax_id"}.issubset(signal_types))
        self.assertIn("[REDACTED_", serialized)
        for raw_value in [
            "Lina Becker",
            "Follow up on payroll dashboard access",
            "Marco Klein",
            "E-31705",
            "Sofia Roth",
            "Lost badge in reception area",
            "Noah Weber",
            "E-20491",
            "24.90 EUR",
            "supplier.owner@example.org",
            "DE123456789",
            "12 Vendor Street",
            "https://drive.example",
        ]:
            self.assertNotIn(raw_value, serialized)

    def test_prelaunch_detector_covers_broad_personal_data_categories_without_raw_values(self) -> None:
        text = "\n".join([
            "Full Name: Alex Morgan",
            "Date of Birth: 1991-03-14",
            "Passport Number: C01X00T55",
            "National ID: 123-45-6789",
            "Driver License: D1234567",
            "Credit Card: 4111 1111 1111 1111",
            "Bank Account: DE89370400440532013000",
            "GPS Location: 52.5200, 13.4050",
            "IP Address: 203.0.113.9",
            "Device ID: 00:1A:2B:3C:4D:5E",
            "Username: @alex_private",
            "Password: hunter2-secret",
            "Medical Record: MRN-881199",
            "Diagnosis: asthma treatment plan",
            "Fingerprint Template: enrolled",
            "DNA Profile: carrier screening",
            "Ethnicity: Hispanic",
            "Political Opinion: local party volunteer",
            "Religion: Buddhist",
            "Trade Union Membership: Unite",
            "Sexual Orientation: bisexual",
            "Criminal Conviction: spent conviction disclosed",
            "Emergency Contact: Jamie Morgan",
            "Student ID: S-88721",
            "Salary: 82000 EUR",
            "Profile URL: https://www.linkedin.com/in/alex-morgan",
            "License Plate: B DS 2049",
        ])

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals)

        self.assertTrue({
            "account_handle",
            "bank_account",
            "biometric_data",
            "credential_secret",
            "criminal_record",
            "date_of_birth",
            "device_identifier",
            "driver_license",
            "family_data",
            "genetic_data",
            "health_data",
            "location_data",
            "medical_identifier",
            "national_identifier",
            "online_identifier",
            "passport_number",
            "payment_card",
            "political_opinion",
            "race_ethnicity",
            "religious_belief",
            "salary_compensation",
            "sex_life_orientation",
            "student_identifier",
            "trade_union",
            "url",
            "license_plate",
        }.issubset(signal_types))
        self.assertNotIn("phone_number", signal_types)
        for raw_value in [
            "Alex Morgan",
            "1991-03-14",
            "C01X00T55",
            "123-45-6789",
            "D1234567",
            "4111 1111 1111 1111",
            "DE89370400440532013000",
            "52.5200, 13.4050",
            "203.0.113.9",
            "00:1A:2B:3C:4D:5E",
            "@alex_private",
            "hunter2-secret",
            "MRN-881199",
            "asthma treatment plan",
            "Hispanic",
            "local party volunteer",
            "Buddhist",
            "Unite",
            "bisexual",
            "spent conviction disclosed",
            "Jamie Morgan",
            "S-88721",
            "82000 EUR",
            "linkedin.com/in/alex-morgan",
            "B DS 2049",
        ]:
            self.assertNotIn(raw_value, serialized)

    def test_google_drive_scan_requires_per_scan_access_token(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            local_root = Path(directory) / "local"
            local_root.mkdir()
            (local_root / "contacts.txt").write_text("Contact Email: stale@example.org", encoding="utf-8")
            with mock.patch.dict("os.environ", {
                "LAWDIT_ENABLE_DEMO_FIXTURES": "false",
                "GOOGLE_CLIENT_ID": "google-client-id",
                "GOOGLE_PICKER_API_KEY": "picker-public-key",
                "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
            }):
                app = build_sqlite_app(db_path, [local_root])
                app.handle(
                    "POST",
                    "/api/sources",
                    "trace_drive_local_create",
                    json.dumps({
                        "sourceId": "source_local_before_drive",
                        "name": "Local before Drive",
                        "sourceType": "local_repo",
                        "rootLabel": str(local_root),
                        "config": {"rootPath": str(local_root)},
                    }),
                    "application/json",
                )
                app.handle("POST", "/api/sources/source_local_before_drive/connect-test", "trace_drive_local_connect")
                app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_drive_local_scan",
                    json.dumps({"sourceId": "source_local_before_drive"}),
                    "application/json",
                )
                time.sleep(1.1)
                stale_findings = app.handle("GET", "/api/findings", "trace_drive_stale_findings")
                created_drive = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_drive_create",
                    json.dumps({
                        "sourceId": "source_drive",
                        "name": "Google Drive Selection",
                        "sourceType": "google_drive_selection",
                        "rootLabel": "Selected Drive folder",
                        "config": {"items": [{"id": "drive-folder-id", "name": "Folder", "mimeType": "application/vnd.google-apps.folder"}]},
                    }),
                    "application/json",
                )
                rejected = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_drive_scan",
                    json.dumps({"sourceId": "source_drive"}),
                    "application/json",
                )
                current_scan = app.handle("GET", "/api/scans/current", "trace_drive_failed_scan")
                findings = app.handle("GET", "/api/findings", "trace_drive_findings_after_failure")
                listed_sources = app.handle("GET", "/api/sources", "trace_drive_sources_after_failure")

        drive_source = next(source for source in listed_sources["body"]["data"] if source["sourceId"] == "source_drive")
        self.assertGreater(len(stale_findings["body"]["data"]), 0)
        self.assertEqual(created_drive["body"]["data"]["status"], "authorization_required")
        self.assertEqual(rejected["status"], 409)
        self.assertIn("short-lived access token", rejected["body"]["detail"])
        self.assertEqual(current_scan["body"]["data"]["status"], "failed")
        self.assertEqual(findings["body"]["data"], [])
        self.assertEqual(drive_source["status"], "authorization_required")

    def test_google_drive_scan_uses_persisted_account_binding_after_refresh(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            documents = SQLiteDocumentStore(db_path)
            auth_service = AuthService(SQLiteAuthStore(documents), auth_settings(), FakeOAuthTransport())
            drive_transport = FakeDriveBindingTransport()
            drive_service = GoogleDriveBindingService(SQLiteDriveBindingStore(documents), auth_service.settings, drive_transport)
            cookie = create_sqlite_session(db_path, "user_drive_bound", "drive-bound")
            drive_service.store.upsert_binding({
                "userId": "user_drive_bound",
                "provider": "google_drive",
                "providerSubject": "google-drive-subject",
                "displayName": "Drive Reviewer",
                "email": "drive.reviewer@example.org",
                "avatarUrl": None,
                "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
                "refreshToken": "stored_drive_refresh",
                "connectedAt": "2026-05-31T00:00:00Z",
                "updatedAt": "2026-05-31T00:00:00Z",
            })
            observed_payloads: list[dict[str, object]] = []

            def fake_reader(source: dict[str, object], payload: dict[str, object]) -> SourceDocumentBatch:
                observed_payloads.append(payload)
                self.assertEqual(source["sourceType"], "google_drive_selection")
                return SourceDocumentBatch(
                    documents=[SourceDocument("contacts.txt", "google-drive://file-id", "Contact Email: drive.owner@example.org", 36, "Google_Drive")],
                    total_files=1,
                    total_bytes=36,
                    unsupported_files=0,
                    warnings=[],
                    family="Google_Drive",
                    extraction_method="google_drive_export",
                )

            with mock.patch.dict("os.environ", {
                "LAWDIT_ENABLE_DEMO_FIXTURES": "false",
                "GOOGLE_CLIENT_ID": "google-client-id",
                "GOOGLE_CLIENT_SECRET": "google-secret",
                "GOOGLE_PICKER_API_KEY": "picker-public-key",
                "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
            }):
                app = SourceHttpApp(
                    auth_service=auth_service,
                    drive_binding_service=drive_service,
                    options=SourceHttpOptions(sqlite_documents=documents, allowed_roots=[]),
                )
                created_drive = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_drive_bound_create",
                    json.dumps({
                        "sourceId": "source_drive_bound",
                        "name": "Bound Drive Selection",
                        "sourceType": "google_drive_selection",
                        "rootLabel": "Selected Drive file",
                        "config": {"items": [{"id": "drive-file-id", "name": "contacts.txt", "mimeType": "text/plain"}]},
                    }),
                    "application/json",
                    {"Cookie": cookie},
                )
                with mock.patch("backend.lawdit.prelaunch_state.read_source_documents", fake_reader):
                    started = app.handle(
                        "POST",
                        "/api/scans/full",
                        "trace_drive_bound_scan",
                        json.dumps({"sourceId": "source_drive_bound"}),
                        "application/json",
                        {"Cookie": cookie},
                    )

        self.assertEqual(created_drive["status"], 201)
        self.assertEqual(created_drive["body"]["data"]["status"], "authorization_required")
        self.assertEqual(started["status"], 202)
        self.assertEqual(drive_transport.refresh_count, 1)
        self.assertEqual(observed_payloads[0]["authorization"], {"googleDriveAccessToken": "drive_refreshed_access"})

    def test_source_registration_strips_runtime_tokens_from_config(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {
                "LAWDIT_ENABLE_DEMO_FIXTURES": "false",
                "GOOGLE_CLIENT_ID": "google-client-id",
                "GOOGLE_PICKER_API_KEY": "picker-public-key",
                "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
            }):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_drive_token_strip",
                    json.dumps({
                        "googleDriveAccessToken": "top-level-token",
                        "sourceId": "source_drive_sanitized",
                        "name": "Google Drive Selection",
                        "sourceType": "google_drive_selection",
                        "rootLabel": "Selected Drive file",
                        "config": {
                            "accessToken": "config-token",
                            "items": [{
                                "id": "drive-file-id",
                                "mimeType": "text/plain",
                                "name": "contacts.txt",
                                "refreshToken": "refresh-token",
                                "url": "https://drive.google.com/file/d/drive-file-id/view",
                            }],
                        },
                    }),
                    "application/json",
                )
                listed = app.handle("GET", "/api/sources", "trace_drive_token_strip_list")
                serialized = json.dumps(listed["body"])

        self.assertEqual(created["status"], 201)
        self.assertNotIn("top-level-token", serialized)
        self.assertNotIn("config-token", serialized)
        self.assertNotIn("refresh-token", serialized)
        self.assertEqual(
            created["body"]["data"]["config"]["items"],
            [{
                "id": "drive-file-id",
                "mimeType": "text/plain",
                "name": "contacts.txt",
                "url": "https://drive.google.com/file/d/drive-file-id/view",
            }],
        )

    def test_source_delete_removes_registration_from_sqlite_store(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_delete_source_create",
                    json.dumps({
                        "sourceId": "source_delete_me",
                        "name": "Delete Me",
                        "sourceType": "remote_file_link",
                        "rootLabel": "https://example.com/delete-me.txt",
                        "config": {"url": "https://example.com/delete-me.txt"},
                    }),
                    "application/json",
                )
                deleted = app.handle("DELETE", "/api/sources/source_delete_me", "trace_delete_source")
                listed = app.handle("GET", "/api/sources", "trace_delete_source_list")
                missing = app.handle("DELETE", "/api/sources/source_delete_me", "trace_delete_source_missing")

        self.assertEqual(created["status"], 201)
        self.assertEqual(deleted["status"], 200)
        self.assertEqual(deleted["body"]["data"]["sourceId"], "source_delete_me")
        self.assertNotIn("source_delete_me", {source["sourceId"] for source in listed["body"]["data"]})
        self.assertEqual(missing["status"], 404)

    def test_created_local_source_cannot_spoof_connected_status(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_local_spoof_create",
                    json.dumps({
                        "sourceId": "source_local_spoof",
                        "name": "Local Source Spoof",
                        "sourceType": "local_repo",
                        "status": "connected",
                        "rootLabel": str(root),
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                rejected = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_local_spoof_scan",
                    json.dumps({"sourceId": "source_local_spoof"}),
                    "application/json",
                )

        self.assertEqual(created["body"]["data"]["status"], "registered")
        self.assertEqual(rejected["status"], 409)

    def test_scan_start_accepts_mock_ready_source(self) -> None:
        app = build_default_app()

        accepted = app.handle(
            "POST",
            "/api/scans/full",
            "trace_test_scan",
            json.dumps({"sourceId": "source_001"}),
            "application/json",
        )

        self.assertEqual(accepted["status"], 202)
        self.assertEqual(accepted["body"]["data"]["status"], "running")
        self.assertEqual(accepted["body"]["data"]["sourceId"], "source_001")
        self.assertTrue(accepted["body"]["meta"]["partial"])

    def test_completed_server_scan_uses_completed_counts(self) -> None:
        app = build_default_app()
        accepted = app.handle(
            "POST",
            "/api/scans/full",
            "trace_test_scan_counts",
            json.dumps({"sourceId": "source_001"}),
            "application/json",
        )

        time.sleep(2.3)
        completed = app.handle("GET", f"/api/scans/{accepted['body']['data']['scanId']}", "trace_test_scan_done")
        metrics = app.handle("GET", "/api/admin/metrics", "trace_test_metrics_done")

        self.assertEqual(completed["body"]["data"]["status"], "completed")
        self.assertEqual(completed["body"]["data"]["flaggedFiles"], 17)
        self.assertEqual(metrics["body"]["data"]["flaggedFiles"], 17)

    def test_non_primary_demo_finding_detail_includes_redacted_context(self) -> None:
        app = build_default_app()

        detail = app.handle("GET", "/api/findings/finding_002", "trace_non_primary_finding")
        serialized = json.dumps(detail["body"])

        self.assertEqual(detail["status"], 200)
        self.assertEqual(detail["body"]["data"]["findingId"], "finding_002")
        self.assertGreater(len(detail["body"]["data"]["signals"]), 0)
        self.assertIn("[REDACTED_EMAIL]", serialized)
        self.assertEqual(detail["body"]["data"]["policyContext"]["policyPackVersion"], "2026.05-demo")
        self.assertFalse(detail["body"]["data"]["signals"][0]["evidenceAnchor"]["rawContentExposed"])
        self.assertFalse(detail["body"]["data"]["auditTimeline"][0]["rawContentExposed"])
        self.assertNotIn("markus.keller@example.org", serialized)

    def test_partial_cached_non_primary_demo_finding_detail_is_repaired(self) -> None:
        app = build_default_app()
        app.demo_state.finding_details["finding_002"] = {
            "auditTimeline": [],
            "evidenceSignalCount": 2,
            "fileName": "old_it_access_request_2020.pdf",
            "findingId": "finding_002",
            "riskLevel": "high",
            "riskScore": 84,
            "status": "open",
        }

        detail = app.handle("GET", "/api/findings/finding_002", "trace_repaired_non_primary_finding")
        serialized = json.dumps(detail["body"])

        self.assertEqual(detail["status"], 200)
        self.assertEqual(detail["body"]["data"]["findingId"], "finding_002")
        self.assertGreater(len(detail["body"]["data"]["signals"]), 0)
        self.assertIn("[REDACTED_EMAIL]", serialized)
        self.assertEqual(detail["body"]["data"]["policyContext"]["policyPackVersion"], "2026.05-demo")
        self.assertFalse(detail["body"]["data"]["signals"][0]["evidenceAnchor"]["rawContentExposed"])
        self.assertNotIn("markus.keller@example.org", serialized)

    def test_review_records_audit_event_without_real_deletion(self) -> None:
        app = build_default_app()
        support = app.handle("GET", "/api/findings/finding_001/review-support", "trace_support")
        checklist_ids = [item["itemId"] for item in support["body"]["data"]["checklist"]]
        reviewed = app.handle(
            "POST",
            "/api/findings/finding_001/review",
            "trace_review",
            json.dumps({
                "actorId": "user_anna",
                "checklistItemIds": checklist_ids,
                "decision": "escalate",
                "nextAction": "legal_escalation",
                "reason": "Needs DPO review before any retention action.",
            }),
            "application/json",
        )
        finding = app.handle("GET", "/api/findings/finding_001", "trace_finding")
        audit_events = app.handle("GET", "/api/audit/events", "trace_audit")

        self.assertEqual(reviewed["status"], 201)
        self.assertFalse(reviewed["body"]["data"]["deletionExecuted"])
        self.assertEqual(finding["body"]["data"]["status"], "escalated")
        self.assertEqual(audit_events["body"]["data"][0]["eventType"], "review_recorded")

    def test_retain_review_updates_retention_status(self) -> None:
        app = build_default_app()
        support = app.handle("GET", "/api/findings/finding_001/review-support", "trace_retain_support")
        checklist_ids = [item["itemId"] for item in support["body"]["data"]["checklist"]]
        reviewed = app.handle(
            "POST",
            "/api/findings/finding_001/review",
            "trace_retain_review",
            json.dumps({
                "actorId": "user_anna",
                "checklistItemIds": checklist_ids,
                "decision": "keep_with_reason",
                "reason": "Business owner confirmed a time-boxed retention exception.",
                "retentionUntil": "2027-05-30",
            }),
            "application/json",
        )
        finding = app.handle("GET", "/api/findings/finding_001", "trace_retain_finding")
        findings = app.handle("GET", "/api/findings", "trace_retain_findings")
        retained_summary = next(item for item in findings["body"]["data"] if item["findingId"] == "finding_001")

        self.assertEqual(reviewed["status"], 201)
        self.assertEqual(finding["body"]["data"]["status"], "retained")
        self.assertEqual(finding["body"]["data"]["retentionStatus"], "retained_until_review")
        self.assertEqual(retained_summary["status"], "retained")
        self.assertEqual(retained_summary["retentionStatus"], "retained_until_review")

    def test_sqlite_app_serves_health_over_real_http(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(build_sqlite_app(db_path)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
                try:
                    connection.request("GET", "/api/health")
                    response = connection.getresponse()
                    payload = json.loads(response.read().decode("utf-8"))
                finally:
                    connection.close()

                self.assertEqual(response.status, 200)
                self.assertTrue(payload["data"]["ok"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_server_deletes_source_over_real_http(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "lawdit.sqlite3"
            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(build_sqlite_app(db_path)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                address = server.server_address
                create_body = json.dumps({
                    "sourceId": "source_http_delete",
                    "name": "HTTP Delete",
                    "sourceType": "remote_file_link",
                    "rootLabel": "https://example.com/http-delete.txt",
                    "config": {"url": "https://example.com/http-delete.txt"},
                })
                connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
                try:
                    connection.request("POST", "/api/sources", body=create_body, headers={"Content-Type": "application/json"})
                    created = connection.getresponse()
                    created.read()
                finally:
                    connection.close()

                connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
                try:
                    connection.request("DELETE", "/api/sources/source_http_delete")
                    deleted = connection.getresponse()
                    payload = json.loads(deleted.read().decode("utf-8"))
                finally:
                    connection.close()

                self.assertEqual(created.status, 201)
                self.assertEqual(deleted.status, 200)
                self.assertEqual(payload["data"]["sourceId"], "source_http_delete")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_server_lists_sources_over_real_http(self) -> None:
        def check(address: tuple[str, int]) -> None:
            connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
            try:
                connection.request("GET", "/api/sources")
                response = connection.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
            finally:
                connection.close()

            self.assertEqual(response.status, 200)
            self.assertGreaterEqual(len(payload["data"]), 1)
            self.assertEqual(dict(response.getheaders())["X-Contract-Version"], "0.1.0")

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(build_default_app()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            check(server.server_address)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_prelaunch_mode_scans_configured_local_source_without_seed_findings(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "contacts.txt").write_text("Contact privacy.reviewer@example.org for this record.", encoding="utf-8")
            db_path = Path(directory) / "lawdit.sqlite3"

            with mock.patch.dict("os.environ", {"LAWDIT_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path, [root])
                initial_sources = app.handle("GET", "/api/sources", "trace_pre_sources")
                initial_findings = app.handle("GET", "/api/findings", "trace_pre_findings")

                created = app.handle(
                    "POST",
                    "/api/sources",
                    "trace_pre_create",
                    json.dumps({
                        "sourceId": "source_local",
                        "name": "Local Source",
                        "sourceType": "local_repo",
                        "status": "registered",
                        "rootLabel": str(root),
                        "masterOfDataUserId": "owner_local",
                        "config": {"rootPath": str(root)},
                    }),
                    "application/json",
                )
                connected = app.handle("POST", "/api/sources/source_local/connect-test", "trace_pre_connect")
                started = app.handle(
                    "POST",
                    "/api/scans/full",
                    "trace_pre_scan",
                    json.dumps({"sourceId": "source_local"}),
                    "application/json",
                )
                time.sleep(1.1)
                completed = app.handle("GET", f"/api/scans/{started['body']['data']['scanId']}", "trace_pre_completed")
                findings = app.handle("GET", "/api/findings", "trace_pre_findings_done")
                detail = app.handle("GET", f"/api/findings/{findings['body']['data'][0]['findingId']}", "trace_pre_finding_detail")
                serialized = json.dumps(detail["body"])

            self.assertEqual(initial_sources["body"]["data"], [])
            self.assertEqual(initial_findings["body"]["data"], [])
            self.assertEqual(created["status"], 201)
            self.assertEqual(connected["body"]["data"]["connectionStatus"], "connected")
            self.assertEqual(started["status"], 202)
            self.assertEqual(completed["body"]["data"]["status"], "completed")
            self.assertEqual(completed["body"]["data"]["totalFiles"], 1)
            self.assertEqual(len(findings["body"]["data"]), 1)
            self.assertIn("[REDACTED_EMAIL]", serialized)
            self.assertNotIn("privacy.reviewer@example.org", serialized)


if __name__ == "__main__":
    unittest.main()
