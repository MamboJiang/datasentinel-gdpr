"""SQLite-backed stores for local demo API persistence."""

from __future__ import annotations

import copy
import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .envelope import utc_now
from .source_store import default_sources, demo_fixtures_enabled, demo_source_ids

SCHEMA_VERSION = "2"
WORKFLOW_STATE_KEY = "demo_workflow_state"


class SQLiteDocumentStore:
    """Owns the local SQLite file used for P0 demo persistence."""

    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path).expanduser()
        self._lock = threading.RLock()
        self._ensure_schema()

    def status(self) -> dict[str, Any]:
        with self._connection() as connection:
            schema_version = connection.execute(
                "SELECT value FROM metadata WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            source_count = connection.execute("SELECT COUNT(*) AS count FROM source_records").fetchone()
            workflow_count = connection.execute("SELECT COUNT(*) AS count FROM workflow_documents").fetchone()
            user_count = connection.execute("SELECT COUNT(*) AS count FROM account_users").fetchone()
            session_count = connection.execute("SELECT COUNT(*) AS count FROM auth_sessions").fetchone()

        return {
            "path": str(self.path),
            "schemaVersion": schema_version["value"] if schema_version else None,
            "accountUserCount": user_count["count"],
            "authSessionCount": session_count["count"],
            "sourceCount": source_count["count"],
            "workflowDocumentCount": workflow_count["count"],
        }

    def seed_sources(self, sources: Iterable[dict[str, Any]]) -> None:
        with self._lock:
            with self._connection() as connection:
                count = connection.execute("SELECT COUNT(*) AS count FROM source_records").fetchone()["count"]
                if count:
                    return

                now = utc_now()
                connection.executemany(
                    """
                    INSERT INTO source_records (source_id, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    [(source["sourceId"], _dump(source), now) for source in sources],
                )

    def clear_demo_fixture_records(self) -> None:
        """Remove historical seeded demo rows when a host switches to prelaunch mode."""

        fixture_ids = demo_source_ids()
        if not fixture_ids:
            return

        placeholders = ",".join("?" for _ in fixture_ids)
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    f"DELETE FROM source_records WHERE source_id IN ({placeholders})",
                    tuple(sorted(fixture_ids)),
                )
                connection.execute(
                    "DELETE FROM workflow_documents WHERE document_key = ?",
                    (WORKFLOW_STATE_KEY,),
                )

    def list_sources(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM source_records ORDER BY source_id"
            ).fetchall()
        return [_load(row["payload_json"]) for row in rows]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM source_records WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return _load(row["payload_json"]) if row else None

    def upsert_source(self, source: dict[str, Any]) -> None:
        now = utc_now()
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO source_records (source_id, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (source["sourceId"], _dump(source), now),
                )

    def delete_source(self, source_id: str) -> dict[str, Any] | None:
        existing = self.get_source(source_id)
        if not existing:
            return None

        with self._lock:
            with self._connection() as connection:
                connection.execute("DELETE FROM source_records WHERE source_id = ?", (source_id,))
        return existing

    def get_workflow_document(self, key: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM workflow_documents WHERE document_key = ?",
                (key,),
            ).fetchone()
        return _load(row["payload_json"]) if row else None

    def put_workflow_document(self, key: str, payload: dict[str, Any]) -> None:
        now = utc_now()
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO workflow_documents (document_key, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(document_key) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (key, _dump(payload), now),
                )

    def _ensure_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._connection() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS source_records (
                        source_id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS workflow_documents (
                        document_key TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS account_users (
                        user_id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        provider_subject TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(provider, provider_subject)
                    );

                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        expires_at INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                connection.execute(
                    """
                    INSERT INTO metadata (key, value)
                    VALUES ('schema_version', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (SCHEMA_VERSION,),
                )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


class SQLiteSourceStore:
    """Persists source records as JSON rows in the local SQLite file."""

    def __init__(
        self,
        documents: SQLiteDocumentStore,
        sources: Iterable[dict[str, Any]] | None = None,
        *,
        allowed_roots: Iterable[Path | str] | None = None,
    ) -> None:
        self.documents = documents
        self.allowed_roots = tuple(Path(root).resolve() for root in (allowed_roots or ()))
        if sources is None and not demo_fixtures_enabled():
            self.documents.clear_demo_fixture_records()
        seed = default_sources() if sources is None else [copy.deepcopy(source) for source in sources]
        self.documents.seed_sources(seed)

    def list_sources(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.documents.list_sources())

    def get(self, source_id: str) -> dict[str, Any] | None:
        source = self.documents.get_source(source_id)
        return copy.deepcopy(source) if source else None

    def add(self, source: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(source)
        self.documents.upsert_source(stored)
        return copy.deepcopy(stored)

    def delete(self, source_id: str) -> dict[str, Any] | None:
        source = self.documents.delete_source(source_id)
        return copy.deepcopy(source) if source else None


class SQLiteWorkflowStore:
    """Persists the mutable demo workflow document in local SQLite."""

    def __init__(self, documents: SQLiteDocumentStore) -> None:
        self.documents = documents

    def load(self) -> dict[str, Any] | None:
        return self.documents.get_workflow_document(WORKFLOW_STATE_KEY)

    def save(self, payload: dict[str, Any]) -> None:
        self.documents.put_workflow_document(WORKFLOW_STATE_KEY, payload)


class SQLiteAuthStore:
    """Persists prelaunch account profiles and first-party sessions."""

    def __init__(self, documents: SQLiteDocumentStore) -> None:
        self.documents = documents

    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        stored = copy.deepcopy(user)
        with self.documents._lock:
            with self.documents._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO account_users (user_id, provider, provider_subject, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(provider, provider_subject) DO UPDATE SET
                        user_id = excluded.user_id,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (stored["userId"], stored["provider"], stored["providerSubject"], _dump(stored), now),
                )
        return copy.deepcopy(stored)

    def create_session(self, user_id: str, expires_at: int) -> str:
        session_id = secrets.token_urlsafe(32)
        with self.documents._lock:
            with self.documents._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO auth_sessions (session_id, user_id, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, expires_at, utc_now()),
                )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.documents._connection() as connection:
            row = connection.execute(
                """
                SELECT s.session_id, s.user_id, s.expires_at, u.payload_json
                FROM auth_sessions s
                JOIN account_users u ON u.user_id = s.user_id
                WHERE s.session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if not row or row["expires_at"] <= int(time.time()):
            return None

        return {
            "sessionId": row["session_id"],
            "userId": row["user_id"],
            "expiresAt": row["expires_at"],
            "user": _load(row["payload_json"]),
        }

    def delete_session(self, session_id: str) -> None:
        with self.documents._lock:
            with self.documents._connection() as connection:
                connection.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(payload_json: str) -> dict[str, Any]:
    return json.loads(payload_json)
