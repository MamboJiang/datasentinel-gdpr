"""DataSentinel demo backend API."""

from .ai_config import (
    AiBudgetSettings,
    AiRuntimeSettings,
    AiSettings,
    OpenRouterSettings,
    load_local_env,
    settings_from_env,
)
from .ai_gateway import AiBudgetGuard, AiRequestRejected, OpenRouterClient
from .processing_pipeline import (
    AiRuntime,
    CandidateSafety,
    EvidenceSignal,
    ProcessingCandidate,
    WorkflowContext,
    build_tier_plan,
)
from .source_api import SourceApi, problem_from_issue
from .source_connection import ConnectionIssue, ConnectionPolicy, SourceConnectionService
from .source_http import SourceHttpApp, build_default_app
from .source_store import SourceStore, default_sources


def make_handler(*args, **kwargs):
    from .source_server import make_handler as build_handler

    return build_handler(*args, **kwargs)

__all__ = [
    "AiBudgetGuard",
    "AiBudgetSettings",
    "AiRequestRejected",
    "AiRuntime",
    "AiRuntimeSettings",
    "AiSettings",
    "CandidateSafety",
    "ConnectionIssue",
    "ConnectionPolicy",
    "EvidenceSignal",
    "OpenRouterClient",
    "OpenRouterSettings",
    "ProcessingCandidate",
    "SourceApi",
    "SourceConnectionService",
    "SourceHttpApp",
    "SourceStore",
    "WorkflowContext",
    "build_default_app",
    "build_tier_plan",
    "default_sources",
    "load_local_env",
    "make_handler",
    "problem_from_issue",
    "settings_from_env",
]
