from __future__ import annotations

import json
import unittest
from decimal import Decimal

from backend.datasentinel.ai_config import settings_from_env
from backend.datasentinel.ai_gateway import AiBudgetGuard, AiRequestRejected, KeySnapshot, ModelPrice
from backend.datasentinel.demo_state import DemoState
from backend.datasentinel.processing_pipeline import (
    AiRuntime,
    CandidateSafety,
    EvidenceSignal,
    ProcessingCandidate,
    build_tier_plan,
)
from backend.datasentinel.source_http import SourceHttpApp


class FakeProvider:
    def __init__(
        self,
        *,
        usage_usd: Decimal = Decimal("0"),
        limit_remaining_usd: Decimal | None = Decimal("100"),
    ) -> None:
        self.usage_usd = usage_usd
        self.limit_remaining_usd = limit_remaining_usd
        self.calls = 0

    def key_snapshot(self) -> KeySnapshot:
        return KeySnapshot(self.usage_usd, self.limit_remaining_usd, "sk-or-v1-redacted")

    def model_price(self, model: str) -> ModelPrice:
        return ModelPrice(Decimal("0.01"), Decimal("0.02"))

    def chat_completion(self, messages: list[dict[str, str]]) -> dict[str, object]:
        self.calls += 1
        return {"choices": [{"message": {"content": "{\"riskHint\":\"review\"}"}}]}


class FailingUsageProvider(FakeProvider):
    def key_snapshot(self) -> KeySnapshot:
        raise AiRequestRejected("network unavailable")


class AiProcessingTests(unittest.TestCase):
    def test_settings_keep_ai_off_without_key(self) -> None:
        settings = settings_from_env({})

        self.assertEqual(settings.status, "disabled")
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.model, "google/gemini-3.1-flash-lite")

    def test_tier_plan_escalates_ambiguous_redacted_evidence(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
        })
        candidate = ProcessingCandidate(EvidenceSignal(
            text_available=True,
            ocr_required=False,
            deterministic_hits=2,
            ambiguous_context=True,
        ))

        steps = build_tier_plan(candidate, settings)
        ai_step = next(step for step in steps if step.tier == "ai_context")

        self.assertEqual(ai_step.status, "ready")
        self.assertEqual(steps[-1].tier, "delta_evaluation_metrics")

    def test_tier_plan_blocks_unredacted_ai_input(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
        })
        candidate = ProcessingCandidate(
            EvidenceSignal(
                text_available=True,
                ocr_required=False,
                deterministic_hits=2,
                ambiguous_context=True,
            ),
            CandidateSafety(redacted=False),
        )

        steps = build_tier_plan(candidate, settings)
        ai_step = next(step for step in steps if step.tier == "ai_context")

        self.assertEqual(ai_step.status, "blocked")

    def test_budget_guard_blocks_after_project_cap(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
            "DATASENTINEL_AI_BUDGET_USD": "25",
            "OPENROUTER_USAGE_BASELINE_USD": "10",
        })
        provider = FakeProvider(usage_usd=Decimal("34.99"))
        guard = AiBudgetGuard(settings, provider)

        decision = guard.preflight(prompt_tokens=1, completion_tokens=1)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "budget_exceeded")

    def test_budget_guard_fails_closed_when_usage_check_fails(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
            "DATASENTINEL_AI_FAIL_CLOSED": "true",
        })
        guard = AiBudgetGuard(settings, FailingUsageProvider())

        decision = guard.preflight(prompt_tokens=1, completion_tokens=1)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "usage_check_failed")

    def test_runtime_rejects_missing_deterministic_anchor(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
        })
        provider = FakeProvider()
        runtime = AiRuntime(settings, provider)

        with self.assertRaises(AiRequestRejected):
            runtime.classify_redacted_context({"redacted": True, "policyPackVersion": "2026.05-demo"})

        self.assertEqual(provider.calls, 0)

    def test_runtime_rejects_missing_policy_context(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
        })
        provider = FakeProvider()
        runtime = AiRuntime(settings, provider)

        with self.assertRaises(AiRequestRejected):
            runtime.classify_redacted_context({"redacted": True, "deterministicSignals": ["email"]})

        self.assertEqual(provider.calls, 0)

    def test_runtime_rejects_unredacted_evidence_before_provider_call(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
        })
        provider = FakeProvider()
        runtime = AiRuntime(settings, provider)

        with self.assertRaises(AiRequestRejected):
            runtime.classify_redacted_context({"redacted": False, "snippet": "raw value"})

        self.assertEqual(provider.calls, 0)

    def test_runtime_counts_accepted_ai_calls(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test",
            "OPENROUTER_USAGE_BASELINE_USD": "0",
        })
        provider = FakeProvider()
        runtime = AiRuntime(settings, provider)

        runtime.classify_redacted_context({
            "redacted": True,
            "snippet": "[REDACTED]",
            "deterministicSignals": ["email"],
            "policyPackVersion": "2026.05-demo",
        })

        summary = runtime.summary()
        self.assertEqual(provider.calls, 1)
        self.assertEqual(summary["modelCalls"], 1)
        self.assertTrue(summary["paidServiceUsed"])
        self.assertEqual(summary["atlasAlignment"][0]["stage"], 1)
        self.assertEqual(summary["atlasAlignment"][-1]["stage"], 12)

    def test_health_exposes_ai_summary_without_secret(self) -> None:
        settings = settings_from_env({
            "DATASENTINEL_AI_MODE": "assistive",
            "OPENROUTER_API_KEY": "sk-test-secret",
            "DATASENTINEL_AI_BUDGET_EUR": "25",
        })
        runtime = AiRuntime(settings, FakeProvider())
        app = SourceHttpApp(demo_state=DemoState(ai_runtime=runtime))

        health = app.handle("GET", "/api/health", "trace_ai_health")
        body = json.dumps(health["body"], sort_keys=True)

        self.assertEqual(health["status"], 200)
        self.assertEqual(health["body"]["data"]["ai"]["status"], "configured")
        self.assertEqual(len(health["body"]["data"]["ai"]["atlasAlignment"]), 12)
        self.assertIn("policy_context_risk", body)
        self.assertIn("ai_context", body)
        self.assertNotIn("sk-test-secret", body)


if __name__ == "__main__":
    unittest.main()
