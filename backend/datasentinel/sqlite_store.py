"""SQLite-backed stores for local demo API persistence."""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .envelope import utc_now
from .source_store import default_sources

SCHEMA_VERSION = "1"
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

        return {
            "path": str(self.path),
            "schemaVersion": schema_version["value"] if schema_version else None,
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


class SQLiteWorkflowStore:
    """Persists the mutable demo workflow document in local SQLite."""

    def __init__(self, documents: SQLiteDocumentStore) -> None:
        self.documents = documents

    def load(self) -> dict[str, Any] | None:
        return self.documents.get_workflow_document(WORKFLOW_STATE_KEY)

    def save(self, payload: dict[str, Any]) -> None:
        self.documents.put_workflow_document(WORKFLOW_STATE_KEY, payload)


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(payload_json: str) -> dict[str, Any]:
    return json.loads(payload_json)
