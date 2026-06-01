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

SCHEMA_VERSION = "4"
WORKFLOW_STATE_KEY = "demo_workflow_state"
OWNER_GLOBAL = "global"
OWNER_LEGACY = "legacy_shared"


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
            drive_binding_count = connection.execute("SELECT COUNT(*) AS count FROM google_drive_bindings").fetchone()

        return {
            "path": str(self.path),
            "schemaVersion": schema_version["value"] if schema_version else None,
            "accountUserCount": user_count["count"],
            "authSessionCount": session_count["count"],
            "googleDriveBindingCount": drive_binding_count["count"],
            "sourceCount": source_count["count"],
            "workflowDocumentCount": workflow_count["count"],
        }

    def seed_sources(self, sources: Iterable[dict[str, Any]], owner_id: str = OWNER_GLOBAL) -> None:
        with self._lock:
            with self._connection() as connection:
                count = connection.execute("SELECT COUNT(*) AS count FROM source_records WHERE owner_id = ?", (owner_id,)).fetchone()["count"]
                if count:
                    return

                now = utc_now()
                connection.executemany(
                    """
                    INSERT INTO source_records (owner_id, source_id, payload_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    [(owner_id, source["sourceId"], _dump(source), now) for source in sources],
                )

    def clear_demo_fixture_records(self, owner_id: str = OWNER_GLOBAL) -> None:
        """Remove historical seeded demo rows when a host switches to prelaunch mode."""

        fixture_ids = demo_source_ids()
        if not fixture_ids:
            return

        placeholders = ",".join("?" for _ in fixture_ids)
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    f"DELETE FROM source_records WHERE owner_id = ? AND source_id IN ({placeholders})",
                    (owner_id, *tuple(sorted(fixture_ids))),
                )
                workflow = connection.execute(
                    "SELECT payload_json FROM workflow_documents WHERE owner_id = ? AND document_key = ?",
                    (owner_id, WORKFLOW_STATE_KEY),
                ).fetchone()
                payload = _load(workflow["payload_json"]) if workflow else None
                if payload and payload.get("stateStoreVersion") != "sqlite-prelaunch-state-v1":
                    connection.execute(
                        "DELETE FROM workflow_documents WHERE owner_id = ? AND document_key = ?",
                        (owner_id, WORKFLOW_STATE_KEY),
                    )

    def list_sources(self, owner_id: str = OWNER_GLOBAL) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM source_records WHERE owner_id = ? ORDER BY source_id",
                (owner_id,),
            ).fetchall()
        return [_load(row["payload_json"]) for row in rows]

    def get_source(self, source_id: str, owner_id: str = OWNER_GLOBAL) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM source_records WHERE owner_id = ? AND source_id = ?",
                (owner_id, source_id),
            ).fetchone()
        return _load(row["payload_json"]) if row else None

    def upsert_source(self, source: dict[str, Any], owner_id: str = OWNER_GLOBAL) -> None:
        now = utc_now()
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO source_records (owner_id, source_id, payload_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(owner_id, source_id) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (owner_id, source["sourceId"], _dump(source), now),
                )

    def delete_source(self, source_id: str, owner_id: str = OWNER_GLOBAL) -> dict[str, Any] | None:
        existing = self.get_source(source_id, owner_id)
        if not existing:
            return None

        with self._lock:
            with self._connection() as connection:
                connection.execute("DELETE FROM source_records WHERE owner_id = ? AND source_id = ?", (owner_id, source_id))
        return existing

    def get_workflow_document(self, key: str, owner_id: str = OWNER_GLOBAL) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM workflow_documents WHERE owner_id = ? AND document_key = ?",
                (owner_id, key),
            ).fetchone()
        return _load(row["payload_json"]) if row else None

    def put_workflow_document(self, key: str, payload: dict[str, Any], owner_id: str = OWNER_GLOBAL) -> None:
        now = utc_now()
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO workflow_documents (owner_id, document_key, payload_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(owner_id, document_key) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (owner_id, key, _dump(payload), now),
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

                    CREATE TABLE IF NOT EXISTS google_drive_bindings (
                        user_id TEXT PRIMARY KEY,
                        provider_subject TEXT NOT NULL,
                        email TEXT,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                self._ensure_owner_scoped_sources(connection)
                self._ensure_owner_scoped_workflows(connection)
                connection.execute(
                    """
                    INSERT INTO metadata (key, value)
                    VALUES ('schema_version', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (SCHEMA_VERSION,),
                )

    def _ensure_owner_scoped_sources(self, connection: sqlite3.Connection) -> None:
        columns = _columns(connection, "source_records")
        if columns and "owner_id" not in columns:
            connection.execute("ALTER TABLE source_records RENAME TO source_records_legacy")
            columns = []
        if not columns:
            connection.execute(
                """
                CREATE TABLE source_records (
                    owner_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner_id, source_id)
                )
                """
            )
        if _columns(connection, "source_records_legacy"):
            connection.execute(
                """
                INSERT OR IGNORE INTO source_records (owner_id, source_id, payload_json, updated_at)
                SELECT ?, source_id, payload_json, updated_at FROM source_records_legacy
                """,
                (OWNER_LEGACY,),
            )
            connection.execute("DROP TABLE source_records_legacy")

    def _ensure_owner_scoped_workflows(self, connection: sqlite3.Connection) -> None:
        columns = _columns(connection, "workflow_documents")
        if columns and "owner_id" not in columns:
            connection.execute("ALTER TABLE workflow_documents RENAME TO workflow_documents_legacy")
            columns = []
        if not columns:
            connection.execute(
                """
                CREATE TABLE workflow_documents (
                    owner_id TEXT NOT NULL,
                    document_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner_id, document_key)
                )
                """
            )
        if _columns(connection, "workflow_documents_legacy"):
            connection.execute(
                """
                INSERT OR IGNORE INTO workflow_documents (owner_id, document_key, payload_json, updated_at)
                SELECT ?, document_key, payload_json, updated_at FROM workflow_documents_legacy
                """,
                (OWNER_LEGACY,),
            )
            connection.execute("DROP TABLE workflow_documents_legacy")

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
        owner_id: str = OWNER_GLOBAL,
    ) -> None:
        self.documents = documents
        self.owner_id = owner_id
        self.allowed_roots = tuple(Path(root).resolve() for root in (allowed_roots or ()))
        if sources is None and not demo_fixtures_enabled():
            self.documents.clear_demo_fixture_records(self.owner_id)
        seed = default_sources() if sources is None else [copy.deepcopy(source) for source in sources]
        self.documents.seed_sources(seed, self.owner_id)

    def list_sources(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.documents.list_sources(self.owner_id))

    def get(self, source_id: str) -> dict[str, Any] | None:
        source = self.documents.get_source(source_id, self.owner_id)
        return copy.deepcopy(source) if source else None

    def add(self, source: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(source)
        self.documents.upsert_source(stored, self.owner_id)
        return copy.deepcopy(stored)

    def delete(self, source_id: str) -> dict[str, Any] | None:
        source = self.documents.delete_source(source_id, self.owner_id)
        return copy.deepcopy(source) if source else None


class SQLiteWorkflowStore:
    """Persists the mutable demo workflow document in local SQLite."""

    def __init__(self, documents: SQLiteDocumentStore, owner_id: str = OWNER_GLOBAL) -> None:
        self.documents = documents
        self.owner_id = owner_id

    def load(self) -> dict[str, Any] | None:
        return self.documents.get_workflow_document(WORKFLOW_STATE_KEY, self.owner_id)

    def save(self, payload: dict[str, Any]) -> None:
        self.documents.put_workflow_document(WORKFLOW_STATE_KEY, payload, self.owner_id)


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


class SQLiteDriveBindingStore:
    """Persists account-scoped Google Drive bindings in local SQLite."""

    def __init__(self, documents: SQLiteDocumentStore) -> None:
        self.documents = documents

    def get_binding(self, user_id: str) -> dict[str, Any] | None:
        with self.documents._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM google_drive_bindings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return _load(row["payload_json"]) if row else None

    def upsert_binding(self, binding: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(binding)
        with self.documents._lock:
            with self.documents._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO google_drive_bindings (user_id, provider_subject, email, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        provider_subject = excluded.provider_subject,
                        email = excluded.email,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        stored["userId"],
                        stored["providerSubject"],
                        stored.get("email"),
                        _dump(stored),
                        utc_now(),
                    ),
                )
        return copy.deepcopy(stored)

    def delete_binding(self, user_id: str) -> dict[str, Any] | None:
        existing = self.get_binding(user_id)
        if not existing:
            return None

        with self.documents._lock:
            with self.documents._connection() as connection:
                connection.execute("DELETE FROM google_drive_bindings WHERE user_id = ?", (user_id,))
        return existing


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(payload_json: str) -> dict[str, Any]:
    return json.loads(payload_json)


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in connection.execute(f"PRAGMA table_info({table})")]
