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
        self.finding_details = {load_mock("findingDetail.json")["data"]["findingId"]: copy.deepcopy(load_mock("findingDetail.json")["data"])}
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
        return response(200, envelope({"ok": True, "server": "datasentinel-agent-us", "ai": self.ai_runtime.summary()}, trace_id), trace_id)

    def get_scan(self, scan_id: str, trace_id: str, path: str) -> dict[str, Any]:
        self._finish_scan_if_ready()

        if scan_id not in {self.scan["scanId"], self._completed_template["scanId"], "scan_001", "current"}:
            return self._not_found("Scan not found", path, trace_id, "#/scanId")

        return response(200, envelope(self.scan, trace_id, partial=self.scan["status"] == "running"), trace_id)

    def get_scan_summary(self, trace_id: str) -> dict[str, Any]:
        self._finish_scan_if_ready()
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

    def list_findings(self, trace_id: str, access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._finish_scan_if_ready()
        findings = self._visible_findings(access_context)
        pagination = {"limit": 25, "offset": 0, "total": len(findings), "nextCursor": None}
        return response(200, envelope(findings, trace_id, pagination=pagination), trace_id)

    def get_finding(self, finding_id: str, trace_id: str, path: str, access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._finish_scan_if_ready()
        finding = self._finding_detail(finding_id)

        if not finding or not _can_view_finding(finding, access_context):
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        return response(200, envelope(finding, trace_id), trace_id)

    def review_finding(self, finding_id: str, payload: dict[str, Any], trace_id: str, path: str, access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        finding = self._finding_detail(finding_id)

        if not finding or not _can_view_finding(finding, access_context):
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        review_support = self._review_support_for(finding, access_context)
        validation = validate_review(review_support, finding_id, payload)

        if validation:
            return self._validation(validation[1], path, trace_id, validation[0])

        decision = payload["decision"]
        resulting_status = DECISION_STATUS[decision]
        review = build_review_record(
            review_support,
            review_support.get("permissionBoundary") or self.permission_boundary,
            self.scan,
            finding_id,
            payload,
            resulting_status,
        )
        audit_event = build_review_audit_event(finding, review)
        self.audit_events.insert(0, audit_event)
        self._update_finding_after_review(finding_id, resulting_status, payload, audit_event, review_support)
        apply_review_metrics(self.metrics, decision)

        return response(201, envelope(review, trace_id), trace_id)

    def audit_event_list(self, trace_id: str) -> dict[str, Any]:
        self._finish_scan_if_ready()
        return response(200, envelope(self.audit_events, trace_id), trace_id)

    def admin_metrics(self, trace_id: str) -> dict[str, Any]:
        self._finish_scan_if_ready()
        return response(200, envelope(self.metrics, trace_id), trace_id)

    def latest_evaluation(self, trace_id: str) -> dict[str, Any]:
        self._finish_scan_if_ready()
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

    def permissions(self, trace_id: str, access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if access_context and access_context.get("permissionBoundary"):
            return response(200, envelope(access_context["permissionBoundary"], trace_id), trace_id)
        return response(200, envelope(self.permission_boundary, trace_id), trace_id)

    def finding_review_support(self, finding_id: str, trace_id: str, path: str, access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._finish_scan_if_ready()
        finding = self._finding_detail(finding_id)
        if not finding or not _can_view_finding(finding, access_context):
            return self._not_found("Finding not found", path, trace_id, "#/findingId")

        support = self._review_support_for(finding, access_context)
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
        aggregation = self.metrics.get("aggregation")
        if isinstance(aggregation, dict) and all(key in aggregation for key in ("inputStages", "scanCoverage", "risk", "ownerBacklog", "outcomes", "audit", "warnings")):
            aggregation.update({"modelCalls": summary["modelCalls"], "estimatedCostUsd": summary["estimatedCostUsd"]})
        else:
            self.metrics.pop("aggregation", None)
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
        connectable_types = {"local_repo", "remote_file_link", "google_drive_selection"}
        ready_statuses = {"connected", "authorization_required"} if source.get("sourceType") == "google_drive_selection" else {"connected"}
        return bool(adapter) and (
            source.get("status") == "mock_ready" and adapter.get("status") == "mock_ready"
            or source.get("sourceType") in connectable_types
            and source.get("status") in ready_statuses
            and adapter.get("status") == "connected"
        )

    def _has_completed_baseline(self, source_id: str, baseline_scan_id: Any) -> bool:
        return self.scan["status"] == "completed" and self.scan["sourceId"] == source_id and (
            baseline_scan_id in (None, "", self.scan["scanId"], "scan_001")
        )

    def _finding_detail(self, finding_id: str) -> dict[str, Any] | None:
        if finding_id not in self.finding_details:
            summary = next((item for item in self.findings if item["findingId"] == finding_id), None)
            if summary:
                self.finding_details[finding_id] = _fallback_finding_detail(summary)

        finding = self.finding_details.get(finding_id)
        if finding:
            _normalize_review_retention_status(finding)

        return self.finding_details.get(finding_id)

    def _visible_findings(self, access_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        for finding in self.findings:
            _normalize_review_retention_status(finding)
        return [copy.deepcopy(finding) for finding in self.findings if _can_view_finding(finding, access_context)]

    def _review_support_for(self, finding: dict[str, Any], access_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not access_context:
            support = copy.deepcopy(self.review_support)
            support["findingId"] = finding["findingId"]
            return support

        return _workspace_review_support(finding, access_context, self.governance_config, self.scan)

    def _update_finding_after_review(
        self,
        finding_id: str,
        resulting_status: str,
        payload: dict[str, Any],
        audit_event: dict[str, Any],
        review_support: dict[str, Any],
    ) -> None:
        transfer_owner = None

        if payload["decision"] == "reassign_owner":
            target = review_target(review_support, payload)
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
                if payload["decision"] == "keep_with_reason":
                    finding["retentionStatus"] = "retained_until_review"
                if transfer_owner:
                    finding["owner"] = transfer_owner

        detail = self.finding_details[finding_id]
        detail["status"] = resulting_status
        if payload["decision"] == "keep_with_reason":
            detail["retentionStatus"] = "retained_until_review"
        if transfer_owner:
            detail["owner"] = transfer_owner
        detail.setdefault("auditTimeline", []).insert(0, copy.deepcopy(audit_event))

    def source_assignment_changed(self, source: dict[str, Any]) -> None:
        if self.scan.get("sourceId") != source.get("sourceId"):
            return

        owner = _source_owner(source)
        for finding in self.findings:
            finding["owner"] = copy.deepcopy(owner) if owner else None
            if not owner:
                finding["status"] = "unassigned"
            elif finding.get("status") == "unassigned":
                finding["status"] = "assigned"
        for detail in self.finding_details.values():
            detail["owner"] = copy.deepcopy(owner) if owner else None
            if not owner:
                detail["status"] = "unassigned"
            elif detail.get("status") == "unassigned":
                detail["status"] = "assigned"

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


DECISION_LABELS = {
    "delete_candidate": "Approve delete (mark candidate)",
    "keep_with_reason": "Retain exception",
    "correct_false_positive": "Correct false positive",
    "reassign_owner": "Transfer to another owner",
    "escalate": "Escalate to DPO or Legal",
}


def _can_view_finding(finding: dict[str, Any], access_context: dict[str, Any] | None) -> bool:
    if not access_context:
        return True

    if not access_context.get("workspace"):
        return True

    actor_id = (access_context.get("actor") or {}).get("accountId")
    if not actor_id:
        return False

    owner = finding.get("owner")
    return isinstance(owner, dict) and owner.get("userId") == actor_id


def _fallback_finding_detail(summary: dict[str, Any]) -> dict[str, Any]:
    detail = copy.deepcopy(summary)
    policy_version = detail.get("policyPackVersion") or "2026.05-demo"
    personal_data_types = [item for item in detail.get("personalDataTypes", []) if isinstance(item, str)] or ["personal_data"]
    signal_limit = max(1, int(detail.get("evidenceSignalCount") or len(personal_data_types) or 1))
    signals = [
        _redacted_mock_signal(detail["findingId"], signal_type, index)
        for index, signal_type in enumerate(personal_data_types[:signal_limit])
    ]

    detail.update({
        "signals": signals,
        "riskExplanation": _fallback_risk_explanation(detail),
        "file": {
            "sourceName": "Controlled demo source",
            "sourceType": "contract_mock",
            "lastModifiedAt": "2026-05-30T12:00:00Z",
            "sizeBytes": None,
        },
        "policyContext": {
            "policyPackId": "policy_gdpr_demo",
            "policyPackVersion": policy_version,
            "policyConclusion": "human_review_required",
        },
        "availableActions": ["delete_candidate", "keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"],
        "deniedActions": [{"action": "execute_real_deletion", "reason": "Real deletion is disabled in the prototype."}],
        "auditTimeline": [_fallback_finding_audit(detail, policy_version)],
    })
    return detail


def _redacted_mock_signal(finding_id: str, signal_type: str, index: int) -> dict[str, Any]:
    label = _human_label(signal_type)
    redacted_token = signal_type.upper()
    snippet = f"{label}: [REDACTED_{redacted_token}]"
    return {
        "type": signal_type,
        "detector": "contract_mock_redacted_signal",
        "confidence": 0.86,
        "snippet": snippet,
        "evidenceAnchor": {
            "anchorId": f"anchor_{finding_id}_{index + 1}",
            "format": "contract_mock",
            "label": label,
            "redactedText": snippet,
            "selector": {
                "type": "summaryEvidence",
                "fieldIndex": index,
                "blockLabel": label,
            },
            "fallback": {
                "label": f"{label} evidence",
                "redactedText": snippet,
            },
            "rawContentExposed": False,
        },
    }


def _fallback_risk_explanation(finding: dict[str, Any]) -> str:
    context = _human_label(str(finding.get("contextCategory") or "unclassified"))
    data_types = ", ".join(_human_label(item) for item in finding.get("personalDataTypes", []) if isinstance(item, str))
    return f"{context} contains redacted {data_types or 'personal data'} evidence that requires accountable human review."


def _fallback_finding_audit(finding: dict[str, Any], policy_version: str) -> dict[str, Any]:
    now = utc_now()
    finding_id = finding["findingId"]
    return {
        "auditEventId": f"audit_{finding_id}_detail",
        "scanId": finding.get("scanId"),
        "findingId": finding_id,
        "eventType": "finding_detail_assembled",
        "actorId": "system",
        "actorType": "system",
        "occurredAt": now,
        "recordedAt": now,
        "auditRecordVersion": "audit-event-v1",
        "objectType": "finding",
        "objectId": finding_id,
        "action": "assemble_redacted_evidence_card",
        "outcome": "assembled",
        "stage": "assembling_findings",
        "summary": "Redacted evidence detail assembled for the controlled demo finding.",
        "rawContentExposed": False,
        "legalConclusionProvided": False,
        "deletionExecuted": False,
        "policyPackVersion": policy_version,
        "evidenceReferences": [{"type": "finding", "id": finding_id, "label": "redacted evidence card"}],
    }


def _human_label(value: str) -> str:
    return value.replace("_", " ").strip().title() or "Unknown"


def _workspace_review_support(
    finding: dict[str, Any],
    access_context: dict[str, Any],
    governance_config: dict[str, Any],
    scan: dict[str, Any],
) -> dict[str, Any]:
    actor_id = (access_context.get("actor") or {}).get("accountId") or "unknown"
    workspace_boundary = access_context.get("permissionBoundary") or {}
    allowed_actions = set(workspace_boundary.get("allowedActions") or [])
    owns_finding = _can_view_finding(finding, access_context)
    can_review = owns_finding and ("review_findings" in allowed_actions or _finding_owner_id(finding) == actor_id)
    decisions = list((governance_config.get("activePolicyPack") or {}).get("reviewDecisions") or DECISION_STATUS.keys())
    available_decisions = [
        {"decision": decision, "requiresReason": True, "label": DECISION_LABELS.get(decision, decision.replace("_", " ").title())}
        for decision in decisions
        if decision in DECISION_STATUS and can_review
    ]
    denied = list(workspace_boundary.get("deniedActions") or [])

    if not can_review:
        denied.extend([
            {
                "action": decision,
                "reason": "Current actor can only record review decisions for findings assigned to them or an explicit review role.",
            }
            for decision in decisions
            if decision in DECISION_STATUS
        ])

    if not any(item.get("action") == "execute_real_deletion" for item in denied):
        denied.append({"action": "execute_real_deletion", "reason": "Real deletion is disabled in P0."})

    boundary = {
        "actorId": actor_id,
        "roles": list(workspace_boundary.get("roles") or []),
        "allowedActions": ["view_assigned_findings", *[item["decision"] for item in available_decisions]] if owns_finding else [],
        "deniedActions": denied,
        "visibleScopes": [f"finding:{finding['findingId']}"] if owns_finding else [],
        "boundaryFingerprint": f"sha256:{actor_id}_{finding['findingId']}_workspace_review_boundary",
        "evaluatedAt": utc_now(),
    }

    return {
        "findingId": finding["findingId"],
        "actorId": actor_id,
        "policyPackVersion": (governance_config.get("activePolicyPack") or {}).get("version", "prelaunch"),
        "plainLanguageSummary": f"This finding is assigned to {(finding.get('owner') or {}).get('displayName') or 'an accountable owner'}. Review decisions must stay inside the Workspace permission boundary.",
        "availableDecisions": available_decisions,
        "checklist": _review_checklist(finding),
        "transferOptions": _transfer_options(access_context, finding) if can_review else [],
        "escalationOptions": _escalation_options(governance_config) if can_review else [],
        "permissionBoundary": boundary,
        "reviewSupportRulesFingerprint": scan.get("reviewSupport", {}).get("supportRulesFingerprint"),
    }


def _review_checklist(finding: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        {"itemId": "review_redacted_evidence", "label": "Review the redacted evidence card and file anchor before deciding.", "required": True},
        {"itemId": "confirm_business_purpose", "label": "Confirm whether a current business purpose exists.", "required": True},
        {"itemId": "confirm_permission_boundary", "label": "Confirm the action is inside the displayed permission boundary.", "required": True},
    ]
    if finding.get("riskLevel") == "high" or finding.get("recommendedAction") == "escalate":
        items.append({"itemId": "consider_escalation_path", "label": "Consider whether the DPO or Legal review path should handle this finding.", "required": True})
    items.append({
        "itemId": "confirm_delete_candidate",
        "label": "Confirm this only marks the file as a deletion candidate and does not execute deletion.",
        "required": True,
        "decision": "delete_candidate",
    })
    return items


def _transfer_options(access_context: dict[str, Any], finding: dict[str, Any]) -> list[dict[str, Any]]:
    owner_id = _finding_owner_id(finding)
    options = []
    for member in access_context.get("members") or []:
        if member.get("accountId") == owner_id or not _member_can_receive_review(member):
            continue
        options.append({
            "userId": member["accountId"],
            "displayName": member.get("displayName") or member["accountId"],
            "email": member.get("email"),
            "reason": "Active Workspace member available for accountable transfer.",
        })
    return options


def _member_can_receive_review(member: dict[str, Any]) -> bool:
    group_ids = set(member.get("groupIds") or [])
    return bool(group_ids & {"workspace_owner", "privacy_reviewer", "data_steward", "dpo_legal"})


def _normalize_review_retention_status(finding: dict[str, Any]) -> None:
    if finding.get("status") == "retained" and finding.get("retentionStatus") in {"needs_review", "review_required", "overdue", None}:
        finding["retentionStatus"] = "retained_until_review"


def _escalation_options(governance_config: dict[str, Any]) -> list[dict[str, str]]:
    paths = (governance_config.get("activePolicyPack") or {}).get("escalationPaths") or []
    return [{"queueId": item.get("pathId") or "legal_escalation", "label": item.get("label") or "Escalate to DPO or Legal"} for item in paths]


def _finding_owner_id(finding: dict[str, Any]) -> str | None:
    owner = finding.get("owner")
    return owner.get("userId") if isinstance(owner, dict) and isinstance(owner.get("userId"), str) else None


def _source_owner(source: dict[str, Any]) -> dict[str, Any] | None:
    owner = source.get("assignedOwner")
    if isinstance(owner, dict) and owner.get("userId"):
        return copy.deepcopy(owner)
    fallback = source.get("fallbackOwner")
    if isinstance(fallback, dict) and fallback.get("userId"):
        return copy.deepcopy(fallback)
    owner_id = source.get("assignedOwnerUserId") or source.get("masterOfDataUserId")
    if isinstance(owner_id, str) and owner_id.strip():
        return {
            "userId": owner_id.strip(),
            "displayName": owner_id.strip(),
            "email": None,
            "assignmentType": "source_master_of_data",
            "assignmentReason": "Configured Source owner receives findings from this Source.",
            "assignmentSource": "source_config",
        }
    return None
