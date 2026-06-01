"""Tier planning for deterministic and AI-assisted scan processing."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from .ai_config import AiSettings, settings_from_env
from .ai_gateway import (
    AiBudgetGuard,
    AiProvider,
    AiRequestRejected,
    OpenRouterClient,
    approx_tokens,
)


@dataclass(frozen=True)
class EvidenceSignal:
    text_available: bool
    ocr_required: bool
    deterministic_hits: int
    ambiguous_context: bool


@dataclass(frozen=True)
class CandidateSafety:
    redacted: bool = True
    policy_pack_available: bool = True


@dataclass(frozen=True)
class WorkflowContext:
    owner_context_available: bool = True
    permission_boundary_available: bool = True
    audit_context_available: bool = True


@dataclass(frozen=True)
class ProcessingCandidate:
    evidence: EvidenceSignal
    safety: CandidateSafety = field(default_factory=CandidateSafety)
    workflow: WorkflowContext = field(default_factory=WorkflowContext)

    @property
    def text_available(self) -> bool:
        return self.evidence.text_available

    @property
    def ocr_required(self) -> bool:
        return self.evidence.ocr_required

    @property
    def deterministic_hits(self) -> int:
        return self.evidence.deterministic_hits

    @property
    def ambiguous_context(self) -> bool:
        return self.evidence.ambiguous_context

    @property
    def redacted(self) -> bool:
        return self.safety.redacted

    @property
    def policy_pack_available(self) -> bool:
        return self.safety.policy_pack_available

    @property
    def owner_context_available(self) -> bool:
        return self.workflow.owner_context_available

    @property
    def permission_boundary_available(self) -> bool:
        return self.workflow.permission_boundary_available

    @property
    def audit_context_available(self) -> bool:
        return self.workflow.audit_context_available


@dataclass(frozen=True)
class TierStep:
    tier: str
    status: str
    reason: str


class AiRuntime:
    def __init__(self, settings: AiSettings, provider: AiProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider or OpenRouterClient(settings)
        self.budget = AiBudgetGuard(settings, self.provider)
        self.model_calls = 0
        self.estimated_cost_usd = Decimal("0")

    @classmethod
    def from_env(cls) -> "AiRuntime":
        return cls(settings_from_env())

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.settings.status,
            "mode": self.settings.mode,
            "provider": "openrouter",
            "model": self.settings.model,
            "budgetLimitEur": float(self.settings.budget_eur),
            "budgetLimitUsd": float(self.settings.budget_usd),
            "usageBaselineUsd": _float_or_none(self.settings.baseline_usage_usd),
            "budgetGuard": "fail_closed" if self.settings.fail_closed else "best_effort",
            "maxPromptTokens": self.settings.max_prompt_tokens,
            "maxCompletionTokens": self.settings.max_completion_tokens,
            "atlasReference": "docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md",
            "atlasAlignment": atlas_alignment(),
            "tierPlan": tier_summary(self.settings),
            "modelCalls": self.model_calls,
            "estimatedCostUsd": float(self.estimated_cost_usd),
            "paidServiceUsed": self.model_calls > 0,
            "rawContentExposed": False,
            "legalConclusionProvided": False,
            "deletionExecuted": False,
        }

    def plan_candidate(self, candidate: ProcessingCandidate) -> list[dict[str, str]]:
        return [step.__dict__ for step in build_tier_plan(candidate, self.settings)]

    def classify_redacted_context(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if not self.settings.enabled:
            raise AiRequestRejected(self.settings.status)
        if evidence.get("redacted") is False:
            raise AiRequestRejected("AI input must be redacted before external processing.")
        if not _has_deterministic_anchor(evidence):
            raise AiRequestRejected("AI input requires deterministic evidence anchors.")
        if not _has_policy_context(evidence):
            raise AiRequestRejected("AI input requires active policy-pack context.")

        prompt = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
        prompt_tokens = min(approx_tokens(prompt), self.settings.max_prompt_tokens)
        decision = self.budget.preflight(prompt_tokens, self.settings.max_completion_tokens)
        if not decision.allowed:
            raise AiRequestRejected(decision.reason)

        messages = [
            {
                "role": "system",
                "content": (
                    "Support lawdit's GDPR Enterprise Expert Atlas workflow using only redacted "
                    "deterministic evidence and policy-pack context. Return concise JSON with "
                    "contextCategory, riskHint, reviewRationale, uncertainty, and humanReviewRequired. "
                    "Do not provide legal advice, compliance claims, owner assignment, permission "
                    "decisions, audit facts, or deletion instructions."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        response = self.provider.chat_completion(messages)
        self.model_calls += 1
        self.estimated_cost_usd += decision.estimated_cost_usd
        return response


def build_tier_plan(candidate: ProcessingCandidate, settings: AiSettings) -> list[TierStep]:
    steps = [
        TierStep("source_policy_context", "ready" if candidate.policy_pack_available else "blocked", "Atlas stage 1 requires source, actor, idempotency, and active policy-pack context."),
        TierStep("metadata_inventory", "enabled", "Atlas stage 2 collects file path, size, modified time, permissions, and fingerprints before content processing."),
        TierStep("text_layer", "ready" if candidate.text_available else "skipped", "Use existing text before OCR."),
    ]
    steps.append(_ocr_step(candidate, settings))
    grep_status = "ready" if candidate.text_available or not candidate.ocr_required else "waiting_for_ocr"
    steps.append(TierStep("grep_rules", grep_status, "Atlas stage 3 runs deterministic local patterns before AI escalation."))
    policy_status = "ready" if candidate.policy_pack_available else "blocked"
    steps.append(TierStep("policy_context_risk", policy_status, "Atlas stage 4 uses policy-pack guidance and redacted signals without legal conclusions."))

    if not candidate.redacted:
        steps.append(TierStep("ai_context", "blocked", "External AI requires redacted evidence only."))
    elif not candidate.policy_pack_available:
        steps.append(TierStep("ai_context", "blocked", "External AI requires active policy-pack context."))
    elif not candidate.ambiguous_context:
        steps.append(TierStep("ai_context", "skipped", "Deterministic stages were sufficient."))
    elif candidate.deterministic_hits <= 0:
        steps.append(TierStep("ai_context", "skipped", "AI requires deterministic evidence anchors."))
    elif settings.enabled:
        steps.append(TierStep("ai_context", "ready", "Escalate only redacted ambiguous Atlas stage-4 context support to OpenRouter."))
    else:
        steps.append(TierStep("ai_context", settings.status, "OpenRouter is not available for this process."))

    steps.extend([
        TierStep("owner_assignment_boundary", "ready" if candidate.owner_context_available else "blocked", "Atlas stage 5 remains deterministic owner or escalation routing, not an AI decision."),
        TierStep("review_permission_boundary", "ready" if candidate.permission_boundary_available else "blocked", "Atlas stages 6-8 keep evidence cards, allowed/denied actions, checklist, and human decisions accountable."),
        TierStep("audit_recording", "ready" if candidate.audit_context_available else "blocked", "Atlas stage 9 records actor, action, state, evidence references, policy context, and safety boundaries."),
        TierStep("delta_evaluation_metrics", "enabled", "Atlas stages 10-12 keep delta governance and evaluation cost/resource metrics visible."),
    ])
    return steps


def tier_summary(settings: AiSettings) -> list[dict[str, Any]]:
    ocr_status = "local_available" if settings.ocr_mode == "local" and shutil.which("tesseract") else settings.ocr_mode
    return [
        {"tier": "source_policy_context", "provider": "local_policy_pack", "mode": "deterministic", "status": "enabled", "atlasStages": [1]},
        {"tier": "metadata_inventory", "provider": "local", "mode": "deterministic", "status": "enabled", "atlasStages": [2]},
        {"tier": "text_layer", "provider": "local", "mode": "deterministic", "status": "enabled", "atlasStages": [2]},
        {"tier": "ocr", "provider": "local_tesseract", "mode": settings.ocr_mode, "status": ocr_status, "atlasStages": [2]},
        {"tier": "grep_rules", "provider": "local_regex", "mode": "deterministic", "status": "enabled", "atlasStages": [3]},
        {"tier": "policy_context_risk", "provider": "local_policy_pack", "mode": "deterministic", "status": "enabled", "atlasStages": [4]},
        {"tier": "ai_context", "provider": "openrouter", "mode": settings.mode, "status": settings.status, "atlasStages": [4], "role": "redacted_context_support_only"},
        {"tier": "owner_assignment_boundary", "provider": "local_governance", "mode": "deterministic", "status": "enabled", "atlasStages": [5]},
        {"tier": "review_permission_boundary", "provider": "local_governance", "mode": "human_accountable", "status": "enabled", "atlasStages": [6, 7, 8]},
        {"tier": "audit_recording", "provider": "local_audit", "mode": "deterministic", "status": "enabled", "atlasStages": [9]},
        {"tier": "delta_evaluation_metrics", "provider": "local_metrics", "mode": "deterministic", "status": "enabled", "atlasStages": [10, 11, 12]},
    ]


def _ocr_step(candidate: ProcessingCandidate, settings: AiSettings) -> TierStep:
    if not candidate.ocr_required:
        return TierStep("ocr", "skipped", "OCR is unnecessary when the text layer is usable.")
    if settings.ocr_mode == "local" and shutil.which("tesseract"):
        return TierStep("ocr", "ready", "Local OCR can run before deterministic matching.")
    return TierStep("ocr", "deferred", "OCR remains recoverable and does not trigger paid AI.")


def _float_or_none(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def atlas_alignment() -> list[dict[str, Any]]:
    return [
        {"stage": 1, "name": "start_full_scan", "boundary": "source, actor, idempotency, and policy-pack context"},
        {"stage": 2, "name": "inventory_and_extraction", "boundary": "metadata, text layer, local/deferred OCR, no raw public content"},
        {"stage": 3, "name": "deterministic_signal_detection", "boundary": "grep/rule anchors before AI"},
        {"stage": 4, "name": "context_and_risk_judgment", "boundary": "policy-pack context and optional redacted AI support, no legal conclusion"},
        {"stage": 5, "name": "owner_assignment", "boundary": "local owner, Master of Data fallback, or escalation routing"},
        {"stage": 6, "name": "finding_evidence_card", "boundary": "redacted evidence, policy context, owner, and audit context"},
        {"stage": 7, "name": "review_support_permission", "boundary": "allowed and denied actions before review"},
        {"stage": 8, "name": "human_review_decision", "boundary": "human reason and no-real-deletion decision record"},
        {"stage": 9, "name": "audit_event_recording", "boundary": "actor, action, evidence references, policy context, and safety flags"},
        {"stage": 10, "name": "incremental_scan", "boundary": "baseline and changed-file governance"},
        {"stage": 11, "name": "admin_metrics", "boundary": "operational counts, backlog, risk, retention, and cost"},
        {"stage": 12, "name": "evaluation_metrics", "boundary": "quality, reproducibility, throughput, and resource intensity"},
    ]


def _has_deterministic_anchor(evidence: Mapping[str, Any]) -> bool:
    anchors = (
        evidence.get("deterministicSignals"),
        evidence.get("evidenceReferences"),
        evidence.get("detectorRulesHash"),
        evidence.get("signalDetectionRulesHash"),
    )
    return any(bool(anchor) for anchor in anchors)


def _has_policy_context(evidence: Mapping[str, Any]) -> bool:
    return bool(evidence.get("policyPackVersion") or evidence.get("policyContext"))
