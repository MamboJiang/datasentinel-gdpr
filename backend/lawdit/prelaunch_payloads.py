"""Small payload factories for prelaunch workflow state."""

from __future__ import annotations

from typing import Any


def failed_scan(scan_id: str, source: dict[str, Any], scan_type: str, warning: str) -> dict[str, Any]:
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


def failed_metrics(warning: str) -> dict[str, Any]:
    return {"totalScannedFiles": 0, "flaggedFiles": 0, "totalScannedGb": 0, "scanProgress": 0, "lastScanTimeSeconds": None, "openReviewBacklog": 0, "highRiskFindings": 0, "retentionOverdueFiles": 0, "extractionWarnings": 1, "reviewDecisionCount": 0, "auditRecordedEvents": 1, "warnings": [warning]}


def failed_evaluation(scan: dict[str, Any], warning: str) -> dict[str, Any]:
    return {"evaluationRunId": f"eval_{scan['scanId']}", "scanId": scan["scanId"], "precision": None, "recall": None, "f1": None, "reproducibility": None, "throughputFilesPerSecond": None, "resourceIntensity": {"modelCalls": 0, "estimatedCostUsd": 0, "paidServiceUsed": False}, "qualityBasis": {"status": "source_unavailable", "warnings": [warning]}}


def empty_scan() -> dict[str, Any]:
    return {"scanId": "current", "sourceId": "", "scanType": "none", "status": "idle", "stage": "not_started", "progress": 0, "totalFiles": 0, "scannedFiles": 0, "flaggedFiles": 0, "totalBytes": 0, "durationMs": None, "throughputFilesPerSecond": None, "reproducibilityFingerprint": None, "pipelineStages": []}


def empty_metrics() -> dict[str, Any]:
    return {"totalScannedFiles": 0, "flaggedFiles": 0, "totalScannedGb": 0, "scanProgress": 0, "lastScanTimeSeconds": None, "openReviewBacklog": 0}


def empty_evaluation() -> dict[str, Any]:
    return {"precision": None, "recall": None, "f1": None, "reproducibility": None, "resourceIntensity": {"modelCalls": 0, "estimatedCostUsd": 0, "paidServiceUsed": False}}


def permission_boundary() -> dict[str, Any]:
    return {"actorId": "authenticated_user", "roles": ["reviewer"], "allowedActions": ["view_assigned_findings", "keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"], "deniedActions": [{"action": "execute_real_deletion", "reason": "Real deletion is disabled."}], "visibleScopes": ["configured_sources"]}


def review_support(finding_id: str) -> dict[str, Any]:
    decisions = ["keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"]
    return {"findingId": finding_id, "actorId": "authenticated_user", "policyPackVersion": "prelaunch", "availableDecisions": [{"decision": decision, "requiresReason": True, "label": decision.replace("_", " ").title()} for decision in decisions], "checklist": [{"itemId": "review_redacted_evidence", "label": "Review redacted evidence before deciding.", "required": True}, {"itemId": "confirm_business_purpose", "label": "Confirm business context.", "required": True}, {"itemId": "confirm_permission_boundary", "label": "Confirm the visible permission boundary.", "required": True}], "escalationOptions": [{"queueId": "legal_escalation", "label": "Escalate to DPO or Legal"}], "permissionBoundary": permission_boundary()}
