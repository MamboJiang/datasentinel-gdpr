"""In-memory P0 workflow state backed by contract mocks."""

from __future__ import annotations

import copy
import time
from typing import Any

from .envelope import envelope, problem, response, utc_now
from .demo_review import (
    DECISION_STATUS,
    apply_review_metrics,
    build_review_audit_event,
    build_review_record,
    review_target,
    validate_review,
)
from .processing_pipeline import AiRuntime
from .source_store import SourceStore, load_mock

SCAN_PROFILES = {
    "full": {
        "scanId": "scan_demo_full",
        "completedFlaggedFiles": 17,
        "progress": 0.34,
        "scannedFiles": 14,
        "flaggedFiles": 5,
        "totalFiles": 42,
        "totalBytes": 38210000,
        "durationMs": 38200,
        "throughputFilesPerSecond": 1.1,
        "delaySeconds": 2.2,
    },
    "delta": {
        "scanId": "scan_demo_delta",
        "completedFlaggedFiles": 2,
        "progress": 0.67,
        "scannedFiles": 4,
        "flaggedFiles": 2,
        "totalFiles": 6,
        "totalBytes": 6240000,
        "durationMs": 5200,
        "throughputFilesPerSecond": 1.15,
        "delaySeconds": 1.8,
    },
}

class DemoState:
    """Serves the P0 contract while keeping demo mutations in memory."""

    def __init__(self, source_store: SourceStore | None = None, ai_runtime: AiRuntime | None = None) -> None:
        self.source_store = source_store or SourceStore()
        self.ai_runtime = ai_runtime or AiRuntime.from_env()
        self.scan = copy.deepcopy(load_mock("scanStatus.json")["data"])
        self.findings = copy.deepcopy(load_mock("myFindings.json")["data"])
        self.finding_details = {
            load_mock("findingDetail.json")["data"]["findingId"]: copy.deepcopy(load_mock("findingDetail.json")["data"])
        }
        self.audit_events = copy.deepcopy(load_mock("auditEvents.json")["data"])
        self.metrics = copy.deepcopy(load_mock("adminMetrics.json")["data"])
        self.evaluation = copy.deepcopy(load_mock("evaluationLatest.json")["data"])
        self.governance_config = copy.deepcopy(load_mock("governanceConfig.json")["data"])
        self.permission_boundary = copy.deepcopy(load_mock("permissionBoundary.json")["data"])
        self.review_support = copy.deepcopy(load_mock("reviewSupport.json")["data"])
        self._running_started_at: float | None = None
        self._completed_template = copy.deepcopy(self.scan)
        self._refresh_ai_runtime_metadata()

    def health(self, trace_id: str) -> dict[str, Any]:
        data = {"ok": True, "server": "datasentinel-agent-us", "ai": self.ai_runtime.summary()}
        return response(200, envelope(data, trace_id), trace_id)

    def get_scan(self, scan_id: str, trace_id: str, path: str) -> dict[str, Any]:
        self._finish_scan_if_ready()

        if scan_id not in {self.scan["scanId"], self._completed_template["scanId"], "scan_001", "current"}:
            return self._not_found("Scan not found", path, trace_id, "#/scanId")

        return response(200, envelope(self.scan, trace_id, partial=self.scan["status"] == "running"), trace_id)

    def get_scan_summary(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.metrics, trace_id), trace_id)

    def start_scan(self, scan_type: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        source_id = payload.get("sourceId")

        if not isinstance(source_id, str) or not source_id:
            return self._validation("sourceId is required", path, trace_id, "#/sourceId")

        source = self.source_store.get(source_id)

        if not source or not self._source_scan_ready(source):
            return self._problem(409, "Source is not scan-ready", path, trace_id, "#/sourceId")

        if scan_type == "delta" and not self._has_completed_baseline(source_id, payload.get("baselineScanId")):
            return self._problem(409, "Delta scan requires a completed selected-source baseline.", path, trace_id, "#/baselineScanId")

        self.scan = self._running_scan(scan_type, source_id)
        self._refresh_ai_runtime_metadata()
        self._running_started_at = time.monotonic()
        self._prepend_audit_event(f"{scan_type}_scan_started", self.scan["scanId"], source_id, "running")
        self.metrics["scanProgress"] = self.scan["progress"]
        self.metrics["totalScannedFiles"] = self.scan["scannedFiles"]
        self.metrics["flaggedFiles"] = self.scan["flaggedFiles"]

        return response(202, envelope(self.scan, trace_id, partial=True, warnings=self._running_warnings()), trace_id)

    def list_findings(self, trace_id: str) -> dict[str, Any]:
        pagination = {"limit": 25, "offset": 0, "total": max(len(self.findings), 17), "nextCursor": None}
        return response(200, envelope(self.findings, trace_id, pagination=pagination), trace_id)

    def get_finding(self, finding_id: str, trace_id: str, path: str) -> dict[str, Any]:
        finding = self._finding_detail(finding_id)

        if not finding:
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        return response(200, envelope(finding, trace_id), trace_id)

    def review_finding(self, finding_id: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        finding = self._finding_detail(finding_id)

        if not finding:
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        validation = validate_review(self.review_support, finding_id, payload)

        if validation:
            return self._validation(validation[1], path, trace_id, validation[0])

        decision = payload["decision"]
        resulting_status = DECISION_STATUS[decision]
        review = build_review_record(
            self.review_support,
            self.permission_boundary,
            self.scan,
            finding_id,
            payload,
            resulting_status,
        )
        audit_event = build_review_audit_event(finding, review)
        self.audit_events.insert(0, audit_event)
        self._update_finding_after_review(finding_id, resulting_status, payload, audit_event)
        apply_review_metrics(self.metrics, decision)

        return response(201, envelope(review, trace_id), trace_id)

    def audit_event_list(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.audit_events, trace_id), trace_id)

    def admin_metrics(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.metrics, trace_id), trace_id)

    def latest_evaluation(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.evaluation, trace_id), trace_id)

    def governance(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.governance_config, trace_id), trace_id)

    def active_policy_pack(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.governance_config["activePolicyPack"], trace_id), trace_id)

    def governance_preview(self, trace_id: str) -> dict[str, Any]:
        preview = {
            "status": "preview_only",
            "affectedFindings": 0,
            "warnings": ["Governance changes are preview-only in P0."],
            "deletionExecuted": False,
        }
        return response(200, envelope(preview, trace_id, warnings=preview["warnings"]), trace_id)

    def permissions(self, trace_id: str) -> dict[str, Any]:
        return response(200, envelope(self.permission_boundary, trace_id), trace_id)

    def finding_review_support(self, finding_id: str, trace_id: str, path: str) -> dict[str, Any]:
        if not self._finding_detail(finding_id):
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        support = copy.deepcopy(self.review_support)
        support["findingId"] = finding_id
        return response(200, envelope(support, trace_id), trace_id)

    def _finish_scan_if_ready(self) -> None:
        if self.scan["status"] != "running" or self._running_started_at is None:
            return

        profile = SCAN_PROFILES.get(self.scan["scanType"], SCAN_PROFILES["full"])

        if time.monotonic() - self._running_started_at < profile["delaySeconds"]:
            return

        self.scan = self._completed_scan(self.scan["scanType"], self.scan["sourceId"], self.scan["scanId"])
        self._refresh_ai_runtime_metadata()
        self._running_started_at = None
        self.metrics["scanProgress"] = 1
        self.metrics["totalScannedFiles"] = self.scan["scannedFiles"]
        self.metrics["flaggedFiles"] = self.scan["flaggedFiles"]
        self.metrics["lastScanTimeSeconds"] = round(self.scan["durationMs"] / 1000)
        self._prepend_audit_event(f"{self.scan['scanType']}_scan_completed", self.scan["scanId"], self.scan["sourceId"], "completed")

    def _running_scan(self, scan_type: str, source_id: str) -> dict[str, Any]:
        profile = SCAN_PROFILES[scan_type]
        scan = copy.deepcopy(self._completed_template)
        scan.update({
            "scanId": profile["scanId"],
            "sourceId": source_id,
            "scanType": scan_type,
            "status": "running",
            "stage": "extracting_content",
            "progress": profile["progress"],
            "totalFiles": profile["totalFiles"],
            "scannedFiles": profile["scannedFiles"],
            "flaggedFiles": profile["flaggedFiles"],
            "totalBytes": profile["totalBytes"],
            "durationMs": None,
            "throughputFilesPerSecond": None,
            "reproducibilityFingerprint": None,
        })
        self._attach_ai_runtime(scan)
        return scan

    def _completed_scan(self, scan_type: str, source_id: str, scan_id: str) -> dict[str, Any]:
        profile = SCAN_PROFILES[scan_type]
        scan = copy.deepcopy(self._completed_template)
        scan.update({
            "scanId": scan_id,
            "sourceId": source_id,
            "scanType": scan_type,
            "status": "completed",
            "stage": "completed",
            "progress": 1,
            "totalFiles": profile["totalFiles"],
            "scannedFiles": profile["totalFiles"],
            "flaggedFiles": profile["completedFlaggedFiles"],
            "totalBytes": profile["totalBytes"],
            "durationMs": profile["durationMs"],
            "throughputFilesPerSecond": profile["throughputFilesPerSecond"],
            "reproducibilityFingerprint": "sha256:demo_delta_findings" if scan_type == "delta" else "sha256:demo_findings",
        })
        self._attach_ai_runtime(scan)
        return scan

    def _refresh_ai_runtime_metadata(self) -> None:
        summary = self.ai_runtime.summary()
        self._attach_ai_runtime(self.scan, summary)
        self.metrics["aiProcessing"] = copy.deepcopy(summary)
        self.metrics.setdefault("aggregation", {})["modelCalls"] = summary["modelCalls"]
        self.metrics.setdefault("aggregation", {})["estimatedCostUsd"] = summary["estimatedCostUsd"]
        self.evaluation["aiProcessing"] = copy.deepcopy(summary)
        self.evaluation.setdefault("resourceIntensity", {})["modelCalls"] = summary["modelCalls"]
        self.evaluation.setdefault("resourceIntensity", {})["estimatedCostUsd"] = summary["estimatedCostUsd"]
        self.evaluation.setdefault("resourceIntensity", {})["paidServiceUsed"] = summary["paidServiceUsed"]

    def _attach_ai_runtime(self, scan: dict[str, Any], summary: dict[str, Any] | None = None) -> None:
        scan["aiProcessing"] = copy.deepcopy(summary or self.ai_runtime.summary())

    def _source_scan_ready(self, source: dict[str, Any]) -> bool:
        adapter = next(
            (item for item in self.governance_config["sourceAdapters"] if item.get("sourceType") == source.get("sourceType")),
            None,
        )
        return bool(adapter) and (
            source.get("status") == "mock_ready" and adapter.get("status") == "mock_ready"
            or source.get("sourceType") == "local_repo" and source.get("status") == "connected" and adapter.get("status") == "connected"
        )

    def _has_completed_baseline(self, source_id: str, baseline_scan_id: Any) -> bool:
        return self.scan["status"] == "completed" and self.scan["sourceId"] == source_id and (
            baseline_scan_id in (None, "", self.scan["scanId"], "scan_001")
        )

    def _finding_detail(self, finding_id: str) -> dict[str, Any] | None:
        if finding_id not in self.finding_details:
            summary = next((item for item in self.findings if item["findingId"] == finding_id), None)
            if summary:
                self.finding_details[finding_id] = {**copy.deepcopy(summary), "auditTimeline": []}

        return self.finding_details.get(finding_id)

    def _update_finding_after_review(
        self,
        finding_id: str,
        resulting_status: str,
        payload: dict[str, Any],
        audit_event: dict[str, Any],
    ) -> None:
        transfer_owner = None

        if payload["decision"] == "reassign_owner":
            target = review_target(self.review_support, payload)
            if target:
                transfer_owner = {
                    "userId": target[0],
                    "displayName": target[1],
                    "email": None,
                    "assignmentType": "delegated",
                    "assignmentReason": "Human reviewer transferred accountability with a recorded reason.",
                    "assignmentSource": "review_transfer",
                }

        for finding in self.findings:
            if finding["findingId"] == finding_id:
                finding["status"] = resulting_status
                if transfer_owner:
                    finding["owner"] = transfer_owner

        detail = self.finding_details[finding_id]
        detail["status"] = resulting_status
        if transfer_owner:
            detail["owner"] = transfer_owner
        detail.setdefault("auditTimeline", []).insert(0, copy.deepcopy(audit_event))

    def _prepend_audit_event(self, event_type: str, scan_id: str, source_id: str, state: str) -> None:
        now = utc_now()
        self.audit_events.insert(0, {
            "auditEventId": f"audit_{int(time.time() * 1000)}",
            "scanId": scan_id,
            "eventType": event_type,
            "actorId": "system" if state == "completed" else "user_demo_admin",
            "actorType": "system" if state == "completed" else "human",
            "occurredAt": now,
            "recordedAt": now,
            "auditRecordVersion": "audit-event-v1",
            "objectType": "scan",
            "objectId": scan_id,
            "action": event_type,
            "outcome": state,
            "stage": self.scan.get("stage"),
            "sourceId": source_id,
            "previousState": None,
            "resultingState": state,
            "summary": f"{event_type.replace('_', ' ').title()} for controlled P0 source.",
            "rawContentExposed": False,
            "legalConclusionProvided": False,
            "deletionExecuted": False,
            "policyPackVersion": self.governance_config["activePolicyPack"]["version"],
        })

    def _running_warnings(self) -> list[str]:
        extraction = self.scan.get("contentExtraction") or {}
        return list(extraction.get("warnings") or [])

    def _validation(self, detail: str, path: str, trace_id: str, pointer: str) -> dict[str, Any]:
        return response(
            422,
            problem(
                status=422,
                title="Request validation failed",
                detail=detail,
                instance=path,
                trace_id=trace_id,
                code="validation-error",
                errors=[{"pointer": pointer, "detail": detail}],
            ),
            trace_id,
            content_type="application/problem+json",
        )

    def _problem(self, status: int, detail: str, path: str, trace_id: str, pointer: str) -> dict[str, Any]:
        return response(
            status,
            problem(
                status=status,
                title="Command rejected",
                detail=detail,
                instance=path,
                trace_id=trace_id,
                code="command-rejected",
                errors=[{"pointer": pointer, "detail": detail}],
            ),
            trace_id,
            content_type="application/problem+json",
        )

    def _not_found(self, detail: str, path: str, trace_id: str, pointer: str) -> dict[str, Any]:
        return response(
            404,
            problem(
                status=404,
                title=detail,
                detail=detail,
                instance=path,
                trace_id=trace_id,
                code="not-found",
                errors=[{"pointer": pointer, "detail": detail}],
            ),
            trace_id,
            content_type="application/problem+json",
        )
