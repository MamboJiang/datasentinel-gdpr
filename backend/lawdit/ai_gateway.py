"""OpenRouter client and budget guard for AI-assisted review support."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from .ai_config import AiSettings

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL_PRICES = {
    "google/gemini-3.1-flash-lite": (Decimal("0.00000025"), Decimal("0.0000015")),
    "openai/gpt-4o-mini": (Decimal("0.00000015"), Decimal("0.0000006")),
    "openai/gpt-4.1-mini": (Decimal("0.0000004"), Decimal("0.0000016")),
}


class AiRequestRejected(RuntimeError):
    """Raised when the AI boundary rejects a request before it leaves the app."""


@dataclass(frozen=True)
class ModelPrice:
    prompt_usd_per_token: Decimal
    completion_usd_per_token: Decimal


@dataclass(frozen=True)
class KeySnapshot:
    usage_usd: Decimal | None
    limit_remaining_usd: Decimal | None
    label: str | None


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str
    estimated_cost_usd: Decimal
    remaining_budget_usd: Decimal | None


class AiProvider(Protocol):
    def key_snapshot(self) -> KeySnapshot:
        ...

    def model_price(self, model: str) -> ModelPrice:
        ...

    def chat_completion(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        ...


class OpenRouterClient:
    def __init__(self, settings: AiSettings) -> None:
        self.settings = settings

    def key_snapshot(self) -> KeySnapshot:
        data = self._request("GET", "/key")
        key_data = data.get("data", {})
        return KeySnapshot(
            usage_usd=_money_or_none(key_data.get("usage")),
            limit_remaining_usd=_money_or_none(key_data.get("limit_remaining")),
            label=key_data.get("label") if isinstance(key_data.get("label"), str) else None,
        )

    def model_price(self, model: str) -> ModelPrice:
        fallback = _default_price(model)
        data = self._request("GET", "/models")
        for item in data.get("data", []):
            if item.get("id") != model:
                continue
            pricing = item.get("pricing", {})
            return ModelPrice(
                prompt_usd_per_token=_money_or_none(pricing.get("prompt")) or fallback.prompt_usd_per_token,
                completion_usd_per_token=_money_or_none(pricing.get("completion")) or fallback.completion_usd_per_token,
            )
        return fallback

    def chat_completion(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "max_completion_tokens": self.settings.max_completion_tokens,
            "temperature": 0.1,
            "stream": False,
        }
        return self._request("POST", "/chat/completions", payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.api_key:
            raise AiRequestRejected("OpenRouter API key is not configured.")

        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{OPENROUTER_API_BASE}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.settings.site_url,
                "X-Title": self.settings.app_title,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise AiRequestRejected(f"OpenRouter request failed with HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            try:
                return self._curl_request(method, path, body)
            except AiRequestRejected as curl_error:
                raise AiRequestRejected(f"OpenRouter request failed: {error}; {curl_error}") from error

    def _curl_request(self, method: str, path: str, body: bytes | None) -> dict[str, Any]:
        if not self.settings.api_key:
            raise AiRequestRejected("OpenRouter API key is not configured.")

        body_path = None
        try:
            config = [
                "silent",
                "show-error",
                "fail-with-body",
                f'url = "{OPENROUTER_API_BASE}{path}"',
                f'request = "{method}"',
                'header = "Accept: application/json"',
                'header = "Content-Type: application/json"',
                f'header = "Authorization: Bearer {_curl_escape(self.settings.api_key)}"',
                f'header = "HTTP-Referer: {_curl_escape(self.settings.site_url)}"',
                f'header = "X-Title: {_curl_escape(self.settings.app_title)}"',
                f"max-time = {self.settings.request_timeout_seconds}",
            ]
            if body is not None:
                with tempfile.NamedTemporaryFile(delete=False) as body_file:
                    body_file.write(body)
                    body_path = body_file.name
                config.append(f'data-binary = "@{body_path}"')

            completed = subprocess.run(
                ["curl", "--config", "-"],
                input="\n".join(config),
                capture_output=True,
                check=False,
                text=True,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip() or "curl failed"
                raise AiRequestRejected(f"OpenRouter curl fallback failed: {detail}")
            return json.loads(completed.stdout)
        except FileNotFoundError as error:
            raise AiRequestRejected("OpenRouter curl fallback is unavailable.") from error
        finally:
            if body_path:
                try:
                    os.unlink(body_path)
                except OSError:
                    pass


class AiBudgetGuard:
    def __init__(self, settings: AiSettings, provider: AiProvider) -> None:
        self.settings = settings
        self.provider = provider

    def preflight(self, prompt_tokens: int, completion_tokens: int) -> BudgetDecision:
        if not self.settings.enabled:
            return BudgetDecision(False, self.settings.status, Decimal("0"), None)

        estimated = self.estimate_cost(prompt_tokens, completion_tokens)
        try:
            snapshot = self.provider.key_snapshot()
        except AiRequestRejected:
            if self.settings.fail_closed:
                return BudgetDecision(False, "usage_check_failed", estimated, None)
            return BudgetDecision(True, "usage_check_skipped", estimated, None)

        remaining_budget = self._remaining_budget(snapshot)
        if remaining_budget is not None and estimated > remaining_budget:
            return BudgetDecision(False, "budget_exceeded", estimated, remaining_budget)
        if snapshot.limit_remaining_usd is not None and estimated > snapshot.limit_remaining_usd:
            return BudgetDecision(False, "openrouter_limit_remaining_exceeded", estimated, snapshot.limit_remaining_usd)
        return BudgetDecision(True, "allowed", estimated, remaining_budget)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        price = self.provider.model_price(self.settings.model)
        prompt_cost = price.prompt_usd_per_token * Decimal(max(prompt_tokens, 0))
        completion_cost = price.completion_usd_per_token * Decimal(max(completion_tokens, 0))
        return prompt_cost + completion_cost

    def _remaining_budget(self, snapshot: KeySnapshot) -> Decimal | None:
        if self.settings.baseline_usage_usd is None or snapshot.usage_usd is None:
            return None
        spent = max(snapshot.usage_usd - self.settings.baseline_usage_usd, Decimal("0"))
        return max(self.settings.budget_usd - spent, Decimal("0"))


def approx_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


def _money_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _default_price(model: str) -> ModelPrice:
    prompt, completion = DEFAULT_MODEL_PRICES.get(model, DEFAULT_MODEL_PRICES["google/gemini-3.1-flash-lite"])
    return ModelPrice(prompt, completion)


def _curl_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
