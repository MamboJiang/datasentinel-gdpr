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

from backend.datasentinel.auth import AUTH_TX_COOKIE, SESSION_COOKIE, AuthService, InMemoryAuthStore
from backend.datasentinel.auth_support import cookie_value, unsign
from backend.datasentinel import build_default_app, make_handler
from backend.datasentinel.source_http import SourceHttpApp, build_sqlite_app
from backend.datasentinel.source_documents import SourceDocument, SourceDocumentBatch


class FakeOAuthTransport:
    def post_form(self, url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, str]:
        self.last_post = {"url": url, "payload": payload, "headers": headers}
        return {"access_token": "provider_token_not_returned", "token_type": "bearer"}

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, object] | list[dict[str, object]]:
        self.last_get = {"url": url, "headers": headers}
        if url.endswith("/user/emails"):
            return [{"email": "privacy.reviewer@example.org", "primary": True, "verified": True}]
        return {"id": 42, "login": "privacy-reviewer", "name": "Privacy Reviewer", "email": None, "avatar_url": "https://avatars.example/reviewer.png"}


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

    def test_auth_required_protects_workflow_routes(self) -> None:
        app = auth_app(auth_required=True)

        rejected = app.handle("GET", "/api/sources", "trace_auth_required")
        session_cookie = start_github_session(app)
        accepted = app.handle("GET", "/api/sources", "trace_auth_sources", None, None, {"Cookie": session_cookie})

        self.assertEqual(rejected["status"], 401)
        self.assertEqual(rejected["contentType"], "application/problem+json")
        self.assertEqual(accepted["status"], 200)

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
            db_path = Path(directory) / "datasentinel.sqlite3"
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
                    "config": {"rootPath": "/tmp/datasentinel-sample"},
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
            db_path = Path(directory) / "datasentinel.sqlite3"
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
            db_path = Path(directory) / "datasentinel.sqlite3"
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

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
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
            db_path = Path(directory) / "datasentinel.sqlite3"

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

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
                app = build_sqlite_app(db_path)
                with mock.patch("backend.datasentinel.source_api.validate_remote_source_url", lambda url: None):
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
                with mock.patch("backend.datasentinel.prelaunch_state.read_source_documents", fake_reader):
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
            db_path = Path(directory) / "datasentinel.sqlite3"
            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
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

    def test_google_drive_scan_requires_per_scan_access_token(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            with mock.patch.dict("os.environ", {
                "DATASENTINEL_ENABLE_DEMO_FIXTURES": "false",
                "GOOGLE_CLIENT_ID": "google-client-id",
                "GOOGLE_PICKER_API_KEY": "picker-public-key",
                "GOOGLE_CLOUD_PROJECT_NUMBER": "1234567890",
            }):
                app = build_sqlite_app(db_path)
                created = app.handle(
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

        self.assertEqual(created["body"]["data"]["status"], "connected")
        self.assertEqual(rejected["status"], 409)
        self.assertIn("short-lived access token", rejected["body"]["detail"])

    def test_source_registration_strips_runtime_tokens_from_config(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
            with mock.patch.dict("os.environ", {
                "DATASENTINEL_ENABLE_DEMO_FIXTURES": "false",
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

    def test_created_local_source_cannot_spoof_connected_status(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            db_path = Path(directory) / "datasentinel.sqlite3"
            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
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

    def test_sqlite_app_serves_health_over_real_http(self) -> None:
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "datasentinel.sqlite3"
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
            db_path = Path(directory) / "datasentinel.sqlite3"

            with mock.patch.dict("os.environ", {"DATASENTINEL_ENABLE_DEMO_FIXTURES": "false"}):
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
