"""Safe source connection checks for P0 demo sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .source_store import SourceStore

EXPECTED_SAMPLE_FAMILIES = {
    "Expense_Report",
    "IT_Access_Request",
    "Incident_Report",
    "Supplier_Onboarding",
    "Training_Evaluation",
}


@dataclass(frozen=True)
class ConnectionPolicy:
    allowed_roots: tuple[Path, ...] = ()

    @classmethod
    def with_roots(cls, roots: list[Path | str]) -> "ConnectionPolicy":
        return cls(tuple(Path(root).resolve() for root in roots))


@dataclass(frozen=True)
class ConnectionIssue(Exception):
    status: int
    code: str
    detail: str
    pointer: str = "#/sourceId"


class SourceConnectionService:
    """Evaluates source reachability without production connector access."""

    def __init__(
        self,
        store: SourceStore | None = None,
        policy: ConnectionPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store or SourceStore()
        roots = policy.allowed_roots if policy else self.store.allowed_roots
        self.policy = policy or ConnectionPolicy(tuple(roots))
        self.clock = clock or (lambda: datetime.now(UTC))

    def connection_result(self, source_id: str) -> tuple[dict[str, Any], bool, list[str]]:
        source = self.store.get(source_id)

        if not source:
            raise ConnectionIssue(404, "source-not-found", "The requested source is not configured.")

        source_type = source.get("sourceType")

        if source_type == "organizer_sample_repo":
            return self._organizer_sample(source)

        if source_type == "sharepoint_mock":
            return self._mock_sharepoint(source), False, []

        if source_type == "local_repo":
            return self._local_repo(source)

        return self._unsupported(source), False, []

    def _organizer_sample(self, source: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str]]:
        diagnostics: list[dict[str, Any]] = []
        warnings: list[str] = []
        reference_url = str(source.get("referenceUrl") or "")

        if _url_has_credentials(reference_url):
            safe_source = {key: value for key, value in source.items() if key != "referenceUrl"}
            return {
                **safe_source,
                "reachable": False,
                "connectionStatus": "unsafe_reference",
                "capabilities": {"canReadMetadata": False, "canReadContent": False},
                "diagnostics": [{
                    "code": "source.reference_credentials",
                    "severity": "error",
                    "message": "Reference URL must not contain credentials or tokens.",
                }],
            }, False, []

        missing = sorted(EXPECTED_SAMPLE_FAMILIES - set(source.get("sampleFamilies") or []))

        if missing:
            diagnostics.append({
                "code": "source.sample_family_missing",
                "severity": "warning",
                "message": "Missing expected sample families.",
                "families": missing,
            })
            warnings.append("Missing expected sample families.")

        return {
            **source,
            "reachable": True,
            "connectionStatus": "degraded" if missing else "connected",
            "capabilities": {"canReadMetadata": True, "canReadContent": False},
            "diagnostics": diagnostics,
        }, bool(missing), warnings

    def _mock_sharepoint(self, source: dict[str, Any]) -> dict[str, Any]:
        return {
            **source,
            "reachable": True,
            "connectionStatus": "mocked",
            "capabilities": {"canReadMetadata": True, "canReadContent": False},
            "diagnostics": [{
                "code": "source.mock_only",
                "severity": "info",
                "message": "Mock source does not claim production SharePoint access.",
            }],
        }

    def _unsupported(self, source: dict[str, Any]) -> dict[str, Any]:
        return {
            **source,
            "reachable": False,
            "connectionStatus": "unsupported_type",
            "capabilities": {"canReadMetadata": False, "canReadContent": False},
            "diagnostics": [{
                "code": "source.unsupported_type",
                "severity": "warning",
                "message": "This source type is registered but not connectable in P0.",
            }],
        }

    def _local_repo(self, source: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str]]:
        root_path = (source.get("config") or {}).get("rootPath")

        if not root_path:
            return self._local_problem(source, "invalid_config", "source.root_path_missing")

        path = Path(root_path)

        if not path.is_absolute():
            return self._local_problem(source, "invalid_config", "source.root_path_relative")

        resolved = path.resolve()

        if not _is_allowed(resolved, self.policy.allowed_roots):
            return self._local_problem(source, "policy_denied", "source.root_path_outside_allowed_roots")

        if not resolved.is_dir():
            return self._local_problem(source, "invalid_config", "source.root_path_not_directory")

        files = [candidate for candidate in resolved.rglob("*") if candidate.is_file()]

        if not files:
            return {
                **source,
                "reachable": True,
                "connectionStatus": "degraded",
                "capabilities": {"canReadMetadata": True, "canReadContent": True},
                "diagnostics": [{
                    "code": "source.local_empty",
                    "severity": "warning",
                    "message": "Local source contains no readable files.",
                }],
            }, True, ["Local source contains no readable files."]

        return {
            **source,
            "reachable": True,
            "connectionStatus": "connected",
            "capabilities": {"canReadMetadata": True, "canReadContent": True},
            "diagnostics": [],
        }, False, []

    def _local_problem(self, source: dict[str, Any], status: str, code: str) -> tuple[dict[str, Any], bool, list[str]]:
        return {
            **source,
            "reachable": False,
            "connectionStatus": status,
            "capabilities": {"canReadMetadata": False, "canReadContent": False},
            "diagnostics": [{
                "code": code,
                "severity": "error",
                "message": "Local source configuration is not allowed in this server context.",
            }],
        }, False, []


def _url_has_credentials(reference_url: str) -> bool:
    parsed = urlparse(reference_url)
    query = parse_qs(parsed.query)
    credential_keys = {"token", "access_token", "password", "key", "secret"}
    return bool(parsed.username or parsed.password or credential_keys.intersection(query))


def _is_allowed(path: Path, roots: tuple[Path, ...]) -> bool:
    if not roots:
        return False

    return any(path == root or root in path.parents for root in roots)
