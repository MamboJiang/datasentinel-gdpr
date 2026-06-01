"""Transient capacity accounting for the public analysis entry."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ACTIVE_ANALYSES = 10
WAITING_SESSION_TTL_SECONDS = 60


@dataclass(frozen=True)
class CapacityReservation:
    session_id: str
    token: str


class PublicAnalysisCapacity:
    def __init__(self, max_active: int = MAX_ACTIVE_ANALYSES, clock: Any = time.time) -> None:
        self.max_active = max(0, int(max_active))
        self.clock = clock
        self._lock = Lock()
        self._active_by_session: dict[str, str] = {}
        self._waiting_by_session: dict[str, float] = {}

    def status(self, session_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            return self._status_locked(session_id)

    def try_begin(self, session_id: str) -> tuple[CapacityReservation | None, dict[str, Any], str | None]:
        with self._lock:
            self._prune_waiting_locked()
            if session_id in self._active_by_session:
                return None, self._status_locked(session_id), "user-active"

            if len(self._active_by_session) >= self.max_active:
                self._waiting_by_session[session_id] = self.clock()
                return None, self._status_locked(session_id), "capacity-full"

            token = hashlib.sha256(f"{session_id}:{self.clock()}".encode("utf-8")).hexdigest()[:16]
            self._waiting_by_session.pop(session_id, None)
            self._active_by_session[session_id] = token
            return CapacityReservation(session_id, token), self._status_locked(session_id), None

    def finish(self, reservation: CapacityReservation) -> None:
        with self._lock:
            if self._active_by_session.get(reservation.session_id) == reservation.token:
                self._active_by_session.pop(reservation.session_id, None)

    def _prune_waiting_locked(self) -> None:
        cutoff = self.clock() - WAITING_SESSION_TTL_SECONDS
        self._waiting_by_session = {
            session_id: timestamp
            for session_id, timestamp in self._waiting_by_session.items()
            if timestamp >= cutoff
        }

    def _status_locked(self, session_id: str | None = None) -> dict[str, Any]:
        self._prune_waiting_locked()
        if len(self._active_by_session) < self.max_active:
            self._waiting_by_session.clear()
        waiting_sessions = sorted(self._waiting_by_session.items(), key=lambda item: item[1])
        active = len(self._active_by_session)
        return {
            "maxActive": self.max_active,
            "activeAnalyses": active,
            "availableSlots": max(0, self.max_active - active),
            "waitingUsers": len(waiting_sessions),
            "queueMode": "capacity_guard",
            "userHasActiveAnalysis": bool(session_id and session_id in self._active_by_session),
            "userQueuePosition": _queue_position(waiting_sessions, session_id),
            "fileSizeLimitBytes": MAX_UPLOAD_BYTES,
        }


def _queue_position(waiting_sessions: list[tuple[str, float]], session_id: str | None) -> int | None:
    if not session_id:
        return None
    for index, (waiting_session, _timestamp) in enumerate(waiting_sessions, start=1):
        if waiting_session == session_id:
            return index
    return None
