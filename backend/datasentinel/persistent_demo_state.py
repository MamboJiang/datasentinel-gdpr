"""Persistent demo workflow state backed by a local document store."""

from __future__ import annotations

import copy
import time
from typing import Any, Protocol

from .demo_state import DemoState
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

    def review_finding(self, finding_id: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        result = super().review_finding(finding_id, payload, trace_id, path)

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
            self._refresh_ai_runtime_metadata()
        self._save_state()

    def start_scan(self, scan_type: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        result = super().start_scan(scan_type, payload, trace_id, path)
        if result["status"] < 400:
            self._running_started_epoch = time.time() if self.scan["status"] == "running" else None
            self._save_state()
        return result

    def review_finding(self, finding_id: str, payload: dict[str, Any], trace_id: str, path: str) -> dict[str, Any]:
        result = super().review_finding(finding_id, payload, trace_id, path)
        if result["status"] < 400:
            self._save_state()
        return result

    def _finish_scan_if_ready(self) -> None:
        before = (self.scan.get("status"), self._pending_result is not None)
        super()._finish_scan_if_ready()
        after = (self.scan.get("status"), self._pending_result is not None)
        if before != after:
            self._running_started_epoch = None if self.scan.get("status") != "running" else self._running_started_epoch
            self._save_state()

    def _restore_state(self, snapshot: dict[str, Any]) -> None:
        for field in WORKFLOW_FIELDS:
            if field in snapshot:
                setattr(self, field, copy.deepcopy(snapshot[field]))

        self._pending_result = copy.deepcopy(snapshot.get("pendingResult"))
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
        snapshot["pendingResult"] = copy.deepcopy(self._pending_result)
        snapshot["runningStartedEpoch"] = self._running_started_epoch
        snapshot["stateStoreVersion"] = "sqlite-prelaunch-state-v1"
        self.workflow_store.save(snapshot)
