"""Prelaunch workflow state that avoids seeded demo findings."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from .demo_state import DemoState, _source_owner
from .deterministic_signals import detect_signals, safe_public_source_path
from .envelope import envelope, response, utc_now
from .source_documents import SourceDocument, SourceDocumentBatch, SourceReadIssue, read_source_documents
from .source_store import SourceStore


class PrelaunchState(DemoState):
    """Uses real configured local files and starts with no seeded findings."""

    def __init__(self, source_store: SourceStore | None = None) -> None:
        super().__init__(source_store)
        self._pending_result: dict[str, Any] | None = None
        self._clear_seeded_workflow()

    def start_scan(self, scan_type: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        source_id = payload.get("sourceId")

        if not isinstance(source_id, str) or not source_id:
            return self._validation("sourceId is required", path, trace_id, "#/sourceId")

        source = self.source_store.get(source_id)

        if not source or not self._source_scan_ready(source):
            return self._problem(409, "Source is not scan-ready", path, trace_id, "#/sourceId")

        try:
            result = _scan_source(source, self.governance_config, scan_type, payload)
        except SourceReadIssue as issue:
            self._record_failed_scan(scan_type, source, issue.detail)
            return self._problem(409, issue.detail, path, trace_id, issue.pointer)

        self._pending_result = result
        self.scan = {**result["scan"], "status": "running", "stage": "detecting_signals", "progress": 0.35}
        self._running_started_at = time.monotonic()
        self._prepend_audit_event(f"{scan_type}_scan_started", self.scan["scanId"], source_id, "running")
        self.metrics.update({
            "scanProgress": self.scan["progress"],
            "totalScannedFiles": 0,
            "flaggedFiles": 0,
        })
        return response(202, envelope(self.scan, trace_id, partial=True), trace_id)

    def _finish_scan_if_ready(self) -> None:
        if self.scan["status"] != "running" or self._running_started_at is None or not self._pending_result:
            return

        if time.monotonic() - self._running_started_at < 1.0:
            return

        result = self._pending_result
        self.scan = result["scan"]
        self.findings = result["findings"]
        self.finding_details = result["findingDetails"]
        self.audit_events = result["auditEvents"] + self.audit_events
        self.metrics = result["metrics"]
        self.evaluation = result["evaluation"]
        self._completed_template = dict(self.scan)
        self._pending_result = None
        self._running_started_at = None
        self._prepend_audit_event(f"{self.scan['scanType']}_scan_completed", self.scan["scanId"], self.scan["sourceId"], "completed")

    def _clear_seeded_workflow(self) -> None:
        self.scan = _empty_scan()
        self._completed_template = dict(self.scan)
        self.findings = []
        self.finding_details = {}
        self.audit_events = []
        self.metrics = _empty_metrics()
        self.evaluation = _empty_evaluation()
        self.review_support = _review_support("")
        self.permission_boundary = _permission_boundary()

    def source_deleted(self, source_id: str) -> None:
        if self.scan.get("sourceId") != source_id:
            return

        self._pending_result = None
        self._running_started_at = None
        self._clear_seeded_workflow()

    def _record_failed_scan(self, scan_type: str, source: dict[str, Any], warning: str) -> None:
        if source.get("sourceType") == "google_drive_selection":
            self.source_store.add({**source, "status": "authorization_required"})

        scan_id = f"scan_failed_{int(time.time() * 1000)}"
        self._pending_result = None
        self._running_started_at = None
        self.scan = _failed_scan(scan_id, source, scan_type, warning)
        self._completed_template = dict(self.scan)
        self.findings = []
        self.finding_details = {}
        self.metrics = _failed_metrics(warning)
        self.evaluation = _failed_evaluation(self.scan, warning)
        self.review_support = _review_support("")
        self._prepend_audit_event(f"{scan_type}_scan_failed", scan_id, source["sourceId"], "failed")


def _scan_source(source: dict[str, Any], governance: dict[str, Any], scan_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    batch = read_source_documents(source, payload)
    scan_id = f"scan_{int(time.time() * 1000)}"
    policy_version = governance.get("activePolicyPack", {}).get("version", "unconfigured")
    findings: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    signal_count = 0
    signal_type_counts: dict[str, int] = {}

    for document in batch.documents:
        signals = detect_signals(document.text)
        if not signals:
            continue

        signal_count += len(signals)
        for signal in signals:
            signal_type_counts[signal["type"]] = signal_type_counts.get(signal["type"], 0) + 1
        finding = _finding(scan_id, source, document, signals, policy_version)
        findings.append({key: value for key, value in finding.items() if key not in {"signals", "riskExplanation", "policyContext", "availableActions", "deniedActions", "auditTimeline", "file"}})
        details[finding["findingId"]] = finding

    audit_events = [_finding_audit(item, policy_version) for item in details.values()]
    scan = _scan(scan_id, source, scan_type, batch, findings, signal_count, signal_type_counts, policy_version)
    metrics = _metrics(scan, findings, batch.unsupported_files)
    evaluation = _evaluation(scan, batch.unsupported_files)
    return {"scan": scan, "findings": findings, "findingDetails": details, "auditEvents": audit_events, "metrics": metrics, "evaluation": evaluation}


def _finding(scan_id: str, source: dict[str, Any], document: SourceDocument, signals: list[dict[str, Any]], policy_version: str) -> dict[str, Any]:
    signal_types = sorted({signal["type"] for signal in signals})
    high_risk_types = {
        "bank_account",
        "biometric_data",
        "credential_secret",
        "criminal_record",
        "date_of_birth",
        "driver_license",
        "employee_id",
        "free_text_personal_context",
        "genetic_data",
        "government_identifier",
        "health_data",
        "iban_like",
        "incident_context",
        "medical_identifier",
        "national_identifier",
        "passport_number",
        "payment_card",
        "political_opinion",
        "race_ethnicity",
        "religious_belief",
        "sex_life_orientation",
        "tax_id",
        "trade_union",
    }
    risk = "high" if any(signal_type in high_risk_types for signal_type in signal_types) else "medium"
    score = 86 if risk == "high" else 64
    owner = _source_owner(source)
    finding_id = "finding_" + hashlib.sha256(f"{scan_id}:{document.source_path}".encode("utf-8")).hexdigest()[:12]
    return {
        "findingId": finding_id,
        "scanId": scan_id,
        "fileName": document.name,
        "sourcePath": safe_public_source_path(document.source_path),
        "riskLevel": risk,
        "riskScore": score,
        "contextCategory": document.family.lower(),
        "personalDataTypes": signal_types,
        "retentionStatus": "needs_review",
        "recommendedAction": "escalate" if risk == "high" else "keep_with_reason",
        "evidenceSignalCount": len(signals),
        "policyPackVersion": policy_version,
        "status": "assigned" if owner else "unassigned",
        "owner": owner,
        "file": {"sourceName": source["name"], "sourceType": source["sourceType"], "lastModifiedAt": utc_now(), "sizeBytes": document.size_bytes},
        "signals": signals,
        "riskExplanation": "The prelaunch scan found redacted identifier patterns that require accountable human review before any action.",
        "policyContext": {"policyPackId": "policy_gdpr_demo", "policyPackVersion": policy_version, "policyConclusion": "human_review_required"},
        "availableActions": ["keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"],
        "deniedActions": [{"action": "execute_real_deletion", "reason": "Real deletion is disabled."}],
        "auditTimeline": [],
    }

def _scan(scan_id: str, source: dict[str, Any], scan_type: str, batch: SourceDocumentBatch, findings: list[dict[str, Any]], signal_count: int, signal_type_counts: dict[str, int], policy_version: str) -> dict[str, Any]:
    warnings = batch.warnings
    extraction_methods = batch.method_counts or [{"method": batch.extraction_method, "files": len(batch.documents), "status": "completed"}]
    recognition_difficulty = batch.recognition_difficulty or {"easy": 0, "moderate": len(batch.documents), "hard": 0, "unsupported": batch.unsupported_files}
    signal_count_items = [{"type": signal_type, "signals": count, "evidenceRequirement": "detector_signal"} for signal_type, count in sorted(signal_type_counts.items())]
    return {
        "scanId": scan_id,
        "sourceId": source["sourceId"],
        "scanType": scan_type,
        "status": "completed",
        "stage": "completed",
        "progress": 1,
        "totalFiles": batch.total_files,
        "scannedFiles": batch.total_files,
        "flaggedFiles": len(findings),
        "totalBytes": batch.total_bytes,
        "durationMs": 1000,
        "throughputFilesPerSecond": batch.total_files,
        "reproducibilityFingerprint": "sha256:" + hashlib.sha256(f"{source['sourceId']}:{batch.total_files}:{signal_count}".encode("utf-8")).hexdigest()[:24],
        "pipelineStages": [{"stage": stage, "status": "completed", "warnings": warnings if stage == "extracting_content" else []} for stage in ["source_ready", "inventorying_files", "extracting_content", "detecting_signals", "judging_context_risk", "assigning_owner", "assembling_findings", "preparing_review_support", "recording_audit_events"]],
        "fileInventory": {"status": "completed", "sourceSnapshotId": f"snapshot_{source['sourceId']}_{scan_id}", "inventoryFingerprint": f"sha256:{scan_id}_inventory", "totalCandidateFiles": batch.total_files, "fingerprintedFiles": batch.total_files, "skippedFiles": 0, "totalBytes": batch.total_bytes, "permissionSnapshots": batch.total_files, "sampleFamilies": [{"family": batch.family, "candidateFiles": batch.total_files, "processedFiles": len(batch.documents), "flaggedFiles": len(findings), "bytes": batch.total_bytes}], "warnings": []},
        "contentExtraction": {"status": "completed", "extractionFingerprint": f"sha256:{scan_id}_{batch.extraction_method}", "processedFiles": batch.total_files, "successfulFiles": len(batch.documents), "warningFiles": batch.unsupported_files, "unsupportedFiles": batch.unsupported_files, "ocrDeferredFiles": batch.ocr_deferred_files, "redactedEvidenceCandidates": signal_count, "rawContentExposed": False, "methods": extraction_methods, "formatCounts": batch.format_counts or [], "recognitionDifficulty": recognition_difficulty, "aiAssistanceUsed": False, "modelCalls": 0, "warnings": warnings},
        "signalDetection": {"status": "completed", "detectorRulesVersion": "prelaunch-local-v2", "detectorRulesHash": f"sha256:{scan_id}_signals", "evidenceRequirements": ["redacted_snippet", "detector_signal", "owner_assignment", "policy_version"], "evaluatedEvidenceCandidates": signal_count, "detectedSignals": signal_count, "redactedSignals": signal_count, "findingsWithSignals": len(findings), "rawContentExposed": False, "signalTypeCounts": signal_count_items, "warnings": []},
        "contextRisk": {"status": "completed", "policyPackVersion": policy_version, "riskRulesFingerprint": f"sha256:{scan_id}_risk", "assessedEvidenceCandidates": signal_count, "contextClassifiedFindings": len(findings), "riskAssessedFindings": len(findings), "highRiskFindings": sum(1 for item in findings if item["riskLevel"] == "high"), "mediumRiskFindings": sum(1 for item in findings if item["riskLevel"] == "medium"), "lowRiskFindings": 0, "retentionReviewFiles": len(findings), "humanReviewRequiredFindings": len(findings), "legalConclusionProvided": False, "contextCategories": [], "warnings": []},
        "ownerAssignment": {"status": "completed", "policyPackVersion": policy_version, "organizationModelVersion": "prelaunch", "ownerResolutionStrategy": "source_owner_then_data_steward_fallback", "assignmentRulesFingerprint": f"sha256:{scan_id}_owner", "humanReviewRequiredFindings": len(findings), "assignedFindings": sum(1 for item in findings if item.get("owner")), "directOwnerAssignments": sum(1 for item in findings if (item.get("owner") or {}).get("assignmentType") == "direct_owner"), "masterOfDataAssignments": sum(1 for item in findings if (item.get("owner") or {}).get("assignmentType") == "data_steward_fallback"), "escalationAssignments": 0, "unownedFindings": sum(1 for item in findings if not item.get("owner")), "transferOptionCount": 0, "escalationOptionCount": 1, "sourceOwnerAvailable": any(item.get("owner") for item in findings), "warnings": []},
        "findingAssembly": {"status": "completed", "policyPackVersion": policy_version, "sourceSnapshotId": f"snapshot_{source['sourceId']}_{scan_id}", "assemblyRulesFingerprint": f"sha256:{scan_id}_assembly", "assembledFindings": len(findings), "evidenceCards": len(findings), "evidenceSignals": signal_count, "redactedEvidenceSnippets": signal_count, "missingEvidenceCards": 0, "deniedActionCount": len(findings), "rawContentExposed": False, "legalConclusionProvided": False, "warnings": []},
        "reviewSupport": {"status": "completed", "policyPackVersion": policy_version, "organizationModelVersion": "prelaunch", "supportRulesFingerprint": f"sha256:{scan_id}_support", "reviewableFindings": len(findings), "supportedFindings": len(findings), "allowedActionCount": 4, "deniedActionCount": 1, "availableDecisionCount": 4, "reasonRequiredDecisionCount": 4, "checklistItemCount": 3, "transferOptionCount": 0, "escalationOptionCount": 1, "rawContentExposed": False, "legalConclusionProvided": False, "warnings": []},
        "auditRecording": {"status": "completed", "policyPackVersion": policy_version, "auditRulesFingerprint": f"sha256:{scan_id}_audit", "recordedEventCount": len(findings), "linkedScanEvents": 1, "linkedFindingEvents": len(findings), "reviewDecisionEvents": 0, "systemEvents": len(findings), "humanEvents": 0, "rawContentExposed": False, "legalConclusionProvided": False, "deletionExecuted": False, "warnings": []},
    }


def _failed_scan(scan_id: str, source: dict[str, Any], scan_type: str, warning: str) -> dict[str, Any]:
    return {
        "scanId": scan_id,
        "sourceId": source["sourceId"],
        "scanType": scan_type,
        "status": "failed",
        "stage": "source_unavailable",
        "progress": 0,
        "totalFiles": 0,
        "scannedFiles": 0,
        "flaggedFiles": 0,
        "totalBytes": 0,
        "durationMs": None,
        "throughputFilesPerSecond": None,
        "reproducibilityFingerprint": None,
        "pipelineStages": [
            {"stage": "source_ready", "status": "failed", "warnings": [warning]},
            {"stage": "inventorying_files", "status": "blocked", "warnings": [warning]},
            {"stage": "extracting_content", "status": "blocked", "warnings": [warning]},
            {"stage": "detecting_signals", "status": "blocked", "warnings": []},
            {"stage": "assembling_findings", "status": "blocked", "warnings": []},
        ],
        "fileInventory": {"status": "failed", "sourceSnapshotId": None, "inventoryFingerprint": None, "totalCandidateFiles": 0, "fingerprintedFiles": 0, "skippedFiles": 0, "totalBytes": 0, "permissionSnapshots": 0, "sampleFamilies": [], "warnings": [warning]},
        "contentExtraction": {"status": "blocked", "processedFiles": 0, "successfulFiles": 0, "warningFiles": 0, "unsupportedFiles": 0, "ocrDeferredFiles": 0, "redactedEvidenceCandidates": 0, "rawContentExposed": False, "methods": [], "formatCounts": [], "recognitionDifficulty": {"easy": 0, "moderate": 0, "hard": 0, "unsupported": 0}, "aiAssistanceUsed": False, "modelCalls": 0, "warnings": [warning]},
        "signalDetection": {"status": "blocked", "detectorRulesVersion": "prelaunch-local-v2", "detectorRulesHash": None, "evidenceRequirements": [], "evaluatedEvidenceCandidates": 0, "detectedSignals": 0, "redactedSignals": 0, "findingsWithSignals": 0, "rawContentExposed": False, "signalTypeCounts": [], "warnings": [warning]},
        "findingAssembly": {"status": "blocked", "assembledFindings": 0, "evidenceCards": 0, "evidenceSignals": 0, "redactedEvidenceSnippets": 0, "missingEvidenceCards": 0, "deniedActionCount": 0, "rawContentExposed": False, "legalConclusionProvided": False, "warnings": [warning]},
    }


def _metrics(scan: dict[str, Any], findings: list[dict[str, Any]], unsupported: int) -> dict[str, Any]:
    return {"totalScannedFiles": scan["scannedFiles"], "flaggedFiles": scan["flaggedFiles"], "totalScannedGb": round(scan["totalBytes"] / 1_000_000_000, 4), "scanProgress": 1, "lastScanTimeSeconds": 1, "openReviewBacklog": len(findings), "highRiskFindings": sum(1 for item in findings if item["riskLevel"] == "high"), "retentionOverdueFiles": 0, "extractionWarnings": unsupported, "reviewDecisionCount": 0, "auditRecordedEvents": len(findings)}


def _failed_metrics(warning: str) -> dict[str, Any]:
    return {"totalScannedFiles": 0, "flaggedFiles": 0, "totalScannedGb": 0, "scanProgress": 0, "lastScanTimeSeconds": None, "openReviewBacklog": 0, "highRiskFindings": 0, "retentionOverdueFiles": 0, "extractionWarnings": 1, "reviewDecisionCount": 0, "auditRecordedEvents": 1, "warnings": [warning]}


def _evaluation(scan: dict[str, Any], unsupported: int) -> dict[str, Any]:
    return {"evaluationRunId": f"eval_{scan['scanId']}", "scanId": scan["scanId"], "precision": None, "recall": None, "f1": None, "reproducibility": None, "throughputFilesPerSecond": scan["throughputFilesPerSecond"], "resourceIntensity": {"modelCalls": 0, "estimatedCostUsd": 0, "paidServiceUsed": False}, "qualityBasis": {"status": "pending_ground_truth", "warnings": [f"{unsupported} unsupported files skipped."] if unsupported else []}}


def _failed_evaluation(scan: dict[str, Any], warning: str) -> dict[str, Any]:
    return {"evaluationRunId": f"eval_{scan['scanId']}", "scanId": scan["scanId"], "precision": None, "recall": None, "f1": None, "reproducibility": None, "throughputFilesPerSecond": None, "resourceIntensity": {"modelCalls": 0, "estimatedCostUsd": 0, "paidServiceUsed": False}, "qualityBasis": {"status": "source_unavailable", "warnings": [warning]}}


def _finding_audit(finding: dict[str, Any], policy_version: str) -> dict[str, Any]:
    now = utc_now()
    event = {"auditEventId": f"audit_{finding['findingId']}", "scanId": finding["scanId"], "findingId": finding["findingId"], "eventType": "finding_assigned", "actorId": "system", "actorType": "system", "occurredAt": now, "recordedAt": now, "summary": "Local prelaunch finding assigned for human review.", "rawContentExposed": False, "legalConclusionProvided": False, "deletionExecuted": False, "policyPackVersion": policy_version}
    finding.setdefault("auditTimeline", []).append(event)
    return event


def _empty_scan() -> dict[str, Any]:
    return {"scanId": "current", "sourceId": "", "scanType": "none", "status": "idle", "stage": "not_started", "progress": 0, "totalFiles": 0, "scannedFiles": 0, "flaggedFiles": 0, "totalBytes": 0, "durationMs": None, "throughputFilesPerSecond": None, "reproducibilityFingerprint": None, "pipelineStages": []}


def _empty_metrics() -> dict[str, Any]:
    return {"totalScannedFiles": 0, "flaggedFiles": 0, "totalScannedGb": 0, "scanProgress": 0, "lastScanTimeSeconds": None, "openReviewBacklog": 0}


def _empty_evaluation() -> dict[str, Any]:
    return {"precision": None, "recall": None, "f1": None, "reproducibility": None, "resourceIntensity": {"modelCalls": 0, "estimatedCostUsd": 0, "paidServiceUsed": False}}


def _permission_boundary() -> dict[str, Any]:
    return {"actorId": "authenticated_user", "roles": ["reviewer"], "allowedActions": ["view_assigned_findings", "keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"], "deniedActions": [{"action": "execute_real_deletion", "reason": "Real deletion is disabled."}], "visibleScopes": ["configured_sources"]}


def _review_support(finding_id: str) -> dict[str, Any]:
    decisions = ["keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"]
    return {"findingId": finding_id, "actorId": "authenticated_user", "policyPackVersion": "prelaunch", "availableDecisions": [{"decision": decision, "requiresReason": True, "label": decision.replace("_", " ").title()} for decision in decisions], "checklist": [{"itemId": "review_redacted_evidence", "label": "Review redacted evidence before deciding.", "required": True}, {"itemId": "confirm_business_purpose", "label": "Confirm business context.", "required": True}, {"itemId": "confirm_permission_boundary", "label": "Confirm the visible permission boundary.", "required": True}], "escalationOptions": [{"queueId": "legal_escalation", "label": "Escalate to DPO or Legal"}], "permissionBoundary": _permission_boundary()}
