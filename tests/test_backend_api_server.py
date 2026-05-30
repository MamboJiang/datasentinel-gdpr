from __future__ import annotations

import http.client
import json
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

from backend.datasentinel import build_default_app, make_handler


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


if __name__ == "__main__":
    unittest.main()
