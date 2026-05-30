"""Human-review helpers for the in-memory demo state."""

from __future__ import annotations

import time
from typing import Any

from .envelope import utc_now

DECISION_STATUS = {
    "delete_candidate": "delete_candidate",
    "keep_with_reason": "retained",
    "correct_false_positive": "false_positive",
    "reassign_owner": "assigned",
    "escalate": "escalated",
}


def validate_review(
    review_support: dict[str, Any],
    finding_id: str,
    payload: dict[str, Any],
) -> tuple[str, str] | None:
    decision = payload.get("decision")
    reason = payload.get("reason")

    if finding_id != payload.get("findingId", finding_id):
        return "#/findingId", "Review request findingId does not match the route."

    if decision not in DECISION_STATUS:
        return "#/decision", "Review decision is not available."

    if not isinstance(reason, str) or not reason.strip():
        return "#/reason", "Review reason is required."

    checklist_ids = set(payload.get("checklistItemIds") or [])
    required_ids = {item["itemId"] for item in review_support["checklist"] if item.get("required")}

    if not required_ids.issubset(checklist_ids):
        return "#/checklistItemIds", "Required review checklist items must be acknowledged."

    if decision == "keep_with_reason" and not payload.get("retentionUntil"):
        return "#/retentionUntil", "Retention review date is required."

    if decision == "reassign_owner" and not payload.get("reassignToUserId"):
        return "#/reassignToUserId", "Transfer target is required."

    if decision == "escalate" and not payload.get("nextAction"):
        return "#/nextAction", "Escalation queue is required."

    return None


def review_target(review_support: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str] | None:
    if payload["decision"] == "reassign_owner":
        target_id = payload.get("reassignToUserId")
        target = next((item for item in review_support.get("transferOptions", []) if item["userId"] == target_id), None)
        return (target["userId"], target["displayName"]) if target else None

    if payload["decision"] == "escalate":
        target_id = payload.get("nextAction")
        target = next((item for item in review_support.get("escalationOptions", []) if item["queueId"] == target_id), None)
        return (target["queueId"], target["label"]) if target else None

    return None


def build_review_record(
    review_support: dict[str, Any],
    permission_boundary: dict[str, Any],
    scan: dict[str, Any],
    finding_id: str,
    payload: dict[str, Any],
    resulting_status: str,
) -> dict[str, Any]:
    now = utc_now()
    target = review_target(review_support, payload)

    return {
        "reviewId": f"review_{int(time.time() * 1000)}",
        "findingId": finding_id,
        "decision": payload["decision"],
        "reason": payload["reason"].strip(),
        "actorId": payload.get("actorId") or review_support["actorId"],
        "createdAt": now,
        "resultingStatus": resulting_status,
        "auditEventId": f"audit_{int(time.time() * 1000)}",
        "targetId": target[0] if target else None,
        "targetLabel": target[1] if target else None,
        "retentionUntil": payload.get("retentionUntil") if payload["decision"] == "keep_with_reason" else None,
        "deletionExecuted": False,
        "policyPackVersion": review_support["policyPackVersion"],
        "permissionBoundaryFingerprint": permission_boundary.get("boundaryFingerprint"),
        "reviewSupportRulesFingerprint": scan.get("reviewSupport", {}).get("supportRulesFingerprint"),
        "idempotencyKey": payload.get("idempotencyKey"),
    }


def build_review_audit_event(finding: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "auditEventId": review["auditEventId"],
        "scanId": finding.get("scanId"),
        "findingId": finding["findingId"],
        "eventType": "review_recorded",
        "actorId": review["actorId"],
        "actorType": "human",
        "occurredAt": review["createdAt"],
        "recordedAt": review["createdAt"],
        "auditRecordVersion": "audit-event-v1",
        "objectType": "review_decision",
        "objectId": finding["findingId"],
        "action": "record_review_decision",
        "outcome": review["resultingStatus"],
        "stage": "recording_audit_events",
        "previousState": finding.get("status", "unknown"),
        "resultingState": review["resultingStatus"],
        "summary": f"Human review recorded: {review['decision']}. Deletion remains simulated.",
        "decision": review["decision"],
        "reason": review["reason"],
        "resultingStatus": review["resultingStatus"],
        "targetId": review.get("targetId"),
        "targetLabel": review.get("targetLabel"),
        "retentionUntil": review.get("retentionUntil"),
        "deletionExecuted": False,
        "policyPackVersion": review.get("policyPackVersion"),
        "permissionBoundaryFingerprint": review.get("permissionBoundaryFingerprint"),
        "reviewSupportRulesFingerprint": review.get("reviewSupportRulesFingerprint"),
        "idempotencyKey": review.get("idempotencyKey"),
        "rawContentExposed": False,
        "legalConclusionProvided": False,
        "evidenceReferences": [
            {"type": "finding", "id": finding["findingId"], "label": "redacted evidence card"},
            {"type": "policy_pack", "id": review.get("policyPackVersion") or "unknown"},
        ],
    }


def apply_review_metrics(metrics: dict[str, Any], decision: str) -> None:
    metrics["reviewDecisionCount"] = metrics.get("reviewDecisionCount", 0) + 1
    metrics["openReviewBacklog"] = max(0, metrics.get("openReviewBacklog", 0) - 1)
    metric_name = {
        "delete_candidate": "deletionCandidateDecisions",
        "keep_with_reason": "retainedDecisions",
        "correct_false_positive": "falsePositiveDecisions",
        "reassign_owner": "reassignedDecisions",
        "escalate": "escalatedDecisions",
    }[decision]
    metrics[metric_name] = metrics.get(metric_name, 0) + 1
    metrics["auditRecordedEvents"] = metrics.get("auditRecordedEvents", 0) + 1
    metrics["auditReviewDecisionEvents"] = metrics.get("auditReviewDecisionEvents", 0) + 1
