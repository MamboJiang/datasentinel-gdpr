"""Persistent demo workflow state backed by a local document store."""

from __future__ import annotations

import copy
import time
from typing import Any, Protocol

from .demo_state import DemoState, _normalize_review_retention_status
from .deterministic_signals import safe_public_source_path, sanitize_public_signal
from .prelaunch_state import PrelaunchState
from .source_store import SourceStore

WORKFLOW_FIELDS = (
    "scan",
    "findings",
    "finding_details",
    "audit_events",
    "metrics",
    "evaluation",
    "governance_config",
    "permission_boundary",
    "review_support",
)


class WorkflowStore(Protocol):
    def load(self) -> dict[str, Any] | None:
        """Return the saved workflow document when one exists."""

    def save(self, payload: dict[str, Any]) -> None:
        """Persist the workflow document."""


class PersistentDemoState(DemoState):
    """Adds restart-safe local persistence to the P0 demo workflow."""

    def __init__(self, source_store: SourceStore, workflow_store: WorkflowStore) -> None:
        self.workflow_store = workflow_store
        self._running_started_epoch: float | None = None
        super().__init__(source_store)
        saved = self.workflow_store.load()

        if saved:
            self._restore_state(saved)
            self._refresh_ai_runtime_metadata()
            self._save_state()
        else:
            self._save_state()

    def start_scan(self, scan_type: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        result = super().start_scan(scan_type, payload, trace_id, path)

        if result["status"] < 400:
            self._running_started_epoch = time.time() if self.scan["status"] == "running" else None
            self._save_state()

        return result

    def get_scan(self, scan_id: str, trace_id: str, path: str) -> dict[str, Any]:
        result = super().get_scan(scan_id, trace_id, path)

        if result["status"] == 200:
            if self.scan["status"] != "running":
                self._running_started_epoch = None
            self._save_state()

        return result

    def review_finding(
        self,
        finding_id: str,
        payload: dict[str, Any],
        trace_id: str,
        path: str,
        access_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = super().review_finding(finding_id, payload, trace_id, path, access_context)

        if result["status"] < 400:
            self._save_state()

        return result

    def _restore_state(self, snapshot: dict[str, Any]) -> None:
        for field in WORKFLOW_FIELDS:
            if field in snapshot:
                setattr(self, field, copy.deepcopy(snapshot[field]))

        epoch = snapshot.get("runningStartedEpoch")
        if self.scan.get("status") == "running" and isinstance(epoch, (int, float)):
            elapsed = max(0, time.time() - epoch)
            self._running_started_epoch = epoch
            self._running_started_at = time.monotonic() - elapsed
        else:
            self._running_started_epoch = None
            self._running_started_at = None

    def _save_state(self) -> None:
        snapshot = {field: copy.deepcopy(getattr(self, field)) for field in WORKFLOW_FIELDS}
        snapshot["runningStartedEpoch"] = self._running_started_epoch
        snapshot["stateStoreVersion"] = "sqlite-demo-state-v1"
        self.workflow_store.save(snapshot)


class PersistentPrelaunchState(PrelaunchState):
    """Adds per-account restart-safe persistence to real prelaunch workflow state."""

    def __init__(self, source_store: SourceStore, workflow_store: WorkflowStore) -> None:
        self.workflow_store = workflow_store
        self._running_started_epoch: float | None = None
        super().__init__(source_store)
        saved = self.workflow_store.load()
        if saved:
            self._restore_state(saved)
            self._clear_missing_source_workflow()
            self._sanitize_persisted_findings()
            self._refresh_ai_runtime_metadata()
        self._save_state()

    def start_scan(self, scan_type: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        result = super().start_scan(scan_type, payload, trace_id, path)
        if result["status"] < 400 or self.scan.get("status") == "failed":
            self._running_started_epoch = time.time() if self.scan["status"] == "running" else None
            self._save_state()
        return result

    def review_finding(
        self,
        finding_id: str,
        payload: dict[str, Any],
        trace_id: str,
        path: str,
        access_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = super().review_finding(finding_id, payload, trace_id, path, access_context)
        if result["status"] < 400:
            self._save_state()
        return result

    def source_assignment_changed(self, source: dict[str, Any]) -> None:
        super().source_assignment_changed(source)
        self._save_state()

    def source_deleted(self, source_id: str) -> None:
        super().source_deleted(source_id)
        if self.scan.get("sourceId") != source_id:
            self._running_started_epoch = None
        self._save_state()

    def _finish_scan_if_ready(self) -> None:
        before = (self.scan.get("status"), self._pending_result is not None)
        super()._finish_scan_if_ready()
        after = (self.scan.get("status"), self._pending_result is not None)
        if before != after:
            self._running_started_epoch = None if self.scan.get("status") != "running" else self._running_started_epoch
            self._save_state()

    def _scan_worker_finished(self, scan_id: str) -> None:
        saved = self.workflow_store.load() or {}
        saved_scan = saved.get("scan")

        if not isinstance(saved_scan, dict) or saved_scan.get("scanId") != scan_id:
            return

        self._running_started_epoch = None if self.scan.get("status") != "running" else self._running_started_epoch
        self._save_state()

    def _restore_state(self, snapshot: dict[str, Any]) -> None:
        for field in WORKFLOW_FIELDS:
            if field in snapshot:
                setattr(self, field, copy.deepcopy(snapshot[field]))

        self._pending_result = copy.deepcopy(snapshot.get("pendingResult"))
        self._source_baselines = copy.deepcopy(snapshot.get("sourceBaselines") or {})
        epoch = snapshot.get("runningStartedEpoch")
        if self.scan.get("status") == "running" and isinstance(epoch, (int, float)):
            elapsed = max(0, time.time() - epoch)
            self._running_started_epoch = epoch
            self._running_started_at = time.monotonic() - elapsed
        else:
            self._running_started_epoch = None
            self._running_started_at = None

    def _clear_missing_source_workflow(self) -> None:
        source_id = self.scan.get("sourceId")
        if isinstance(source_id, str) and source_id and not self.source_store.get(source_id):
            self._pending_result = None
            self._running_started_epoch = None
            self._running_started_at = None
            self._clear_seeded_workflow()

    def _sanitize_persisted_findings(self) -> None:
        for finding in self.findings:
            _sanitize_finding_record(finding)
        for finding in self.finding_details.values():
            _sanitize_finding_record(finding)

    def _save_state(self) -> None:
        snapshot = {field: copy.deepcopy(getattr(self, field)) for field in WORKFLOW_FIELDS}
        snapshot["pendingResult"] = copy.deepcopy(self._pending_result)
        snapshot["sourceBaselines"] = copy.deepcopy(self._source_baselines)
        snapshot["runningStartedEpoch"] = self._running_started_epoch
        snapshot["stateStoreVersion"] = "sqlite-prelaunch-state-v1"
        self.workflow_store.save(snapshot)


def _sanitize_finding_record(finding: dict[str, Any]) -> None:
    _normalize_review_retention_status(finding)

    source_path = finding.get("sourcePath")
    if isinstance(source_path, str):
        finding["sourcePath"] = safe_public_source_path(source_path)

    signals = finding.get("signals")
    if isinstance(signals, list):
        finding["signals"] = [sanitize_public_signal(signal) if isinstance(signal, dict) else signal for signal in signals]
