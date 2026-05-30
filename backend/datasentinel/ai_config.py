"""AI runtime configuration for the local DataSentinel server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "google/gemini-3.1-flash-lite"


def load_local_env(path: Path | None = None) -> None:
    """Load ignored local env values without overriding the process environment."""

    env_path = path or PROJECT_ROOT / ".env.local"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str | None
    model: str
    site_url: str
    app_title: str


@dataclass(frozen=True)
class AiBudgetSettings:
    budget_eur: Decimal
    budget_usd: Decimal
    baseline_usage_usd: Decimal | None
    fail_closed: bool


@dataclass(frozen=True)
class AiRuntimeSettings:
    max_prompt_tokens: int
    max_completion_tokens: int
    request_timeout_seconds: float
    ocr_mode: str


@dataclass(frozen=True)
class AiSettings:
    mode: str
    openrouter: OpenRouterSettings
    budget: AiBudgetSettings
    runtime: AiRuntimeSettings

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def enabled(self) -> bool:
        return self.mode == "assistive" and self.configured

    @property
    def status(self) -> str:
        if self.mode == "off":
            return "disabled"
        if not self.configured:
            return "missing_api_key"
        if self.enabled:
            return "configured"
        return "disabled"

    @property
    def api_key(self) -> str | None:
        return self.openrouter.api_key

    @property
    def model(self) -> str:
        return self.openrouter.model

    @property
    def site_url(self) -> str:
        return self.openrouter.site_url

    @property
    def app_title(self) -> str:
        return self.openrouter.app_title

    @property
    def budget_eur(self) -> Decimal:
        return self.budget.budget_eur

    @property
    def budget_usd(self) -> Decimal:
        return self.budget.budget_usd

    @property
    def baseline_usage_usd(self) -> Decimal | None:
        return self.budget.baseline_usage_usd

    @property
    def fail_closed(self) -> bool:
        return self.budget.fail_closed

    @property
    def max_prompt_tokens(self) -> int:
        return self.runtime.max_prompt_tokens

    @property
    def max_completion_tokens(self) -> int:
        return self.runtime.max_completion_tokens

    @property
    def request_timeout_seconds(self) -> float:
        return self.runtime.request_timeout_seconds

    @property
    def ocr_mode(self) -> str:
        return self.runtime.ocr_mode


def settings_from_env(env: Mapping[str, str] | None = None) -> AiSettings:
    values = env or os.environ
    return AiSettings(
        mode=_text(values, "DATASENTINEL_AI_MODE", "off").lower(),
        openrouter=OpenRouterSettings(
            api_key=_secret(values, "OPENROUTER_API_KEY"),
            model=_text(values, "OPENROUTER_MODEL", DEFAULT_MODEL),
            site_url=_text(values, "OPENROUTER_SITE_URL", "https://founder-force.uk/"),
            app_title=_text(values, "OPENROUTER_APP_TITLE", "DataSentinel GDPR"),
        ),
        budget=AiBudgetSettings(
            budget_eur=_decimal(values, "DATASENTINEL_AI_BUDGET_EUR", "25.00"),
            budget_usd=_decimal(values, "DATASENTINEL_AI_BUDGET_USD", "25.00"),
            baseline_usage_usd=_optional_decimal(values, "OPENROUTER_USAGE_BASELINE_USD"),
            fail_closed=_boolean(values, "DATASENTINEL_AI_FAIL_CLOSED", True),
        ),
        runtime=AiRuntimeSettings(
            max_prompt_tokens=_integer(values, "DATASENTINEL_AI_MAX_PROMPT_TOKENS", 6000),
            max_completion_tokens=_integer(values, "DATASENTINEL_AI_MAX_COMPLETION_TOKENS", 350),
            request_timeout_seconds=float(_decimal(values, "DATASENTINEL_AI_TIMEOUT_SECONDS", "20")),
            ocr_mode=_text(values, "DATASENTINEL_OCR_MODE", "deferred").lower(),
        ),
    )


def _text(values: Mapping[str, str], key: str, default: str) -> str:
    value = values.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _secret(values: Mapping[str, str], key: str) -> str | None:
    value = values.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _integer(values: Mapping[str, str], key: str, default: int) -> int:
    value = values.get(key)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _decimal(values: Mapping[str, str], key: str, default: str) -> Decimal:
    return _optional_decimal(values, key) or Decimal(default)


def _optional_decimal(values: Mapping[str, str], key: str) -> Decimal | None:
    value = values.get(key)
    if value is None or not value.strip():
        return None
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation:
        return None
    return parsed if parsed >= 0 else None


def _boolean(values: Mapping[str, str], key: str, default: bool) -> bool:
    value = values.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
